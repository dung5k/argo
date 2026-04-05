import os
import glob
import json
import torch
import pandas as pd
from torch.utils.data import DataLoader
from train_ga import TransformerModel, TimeSeriesDataset, device

def evaluate_model(model, features, targets, threshold):
    dataset = TimeSeriesDataset(features, targets, window_size=60)
    # Ensure window_size aligns with training
    loader = DataLoader(dataset, batch_size=512, shuffle=False)
    
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
            outputs = model(batch_x)
            
            probs = torch.softmax(outputs.data, dim=1)
            max_probs, predicted = torch.max(probs, 1)
            
            confident_mask = max_probs > threshold
            confident_preds = predicted[confident_mask]
            confident_targets = batch_y[confident_mask]
            
            total += confident_preds.size(0)
            correct += (confident_preds == confident_targets).sum().item()
            
    win_rate = (correct / total) * 100 if total > 0 else 0
    return correct, total, win_rate

def main():
    print(f"\n=================================================")
    print(f"🚀 ENGINE BACKTEST ĐỘC LẬP - KIỂM KIẾM THÁNG 10/2025 🚀")
    print(f"=================================================\n")
    
    base_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor"
    data_path = os.path.join(base_path, "data")
    runs_path = os.path.join(base_path, "runs")
    
    # 1. Tìm thư mục huấn luyện mới nhất
    search_pattern = os.path.join(runs_path, "*xauusd_TRANSFORMER*")
    folders = glob.glob(search_pattern)
    if not folders:
        print("Không tìm thấy folder runs nào chứa trọng số v3!")
        return
        
    latest_folder = max(folders, key=os.path.getmtime)
    print(f"Đang phân tích bộ não từ: {os.path.basename(latest_folder)}")
    
    # 2. Đọc Metrix để lấy Cấu trúc Não
    metrix_file = os.path.join(latest_folder, "training_metrix.json")
    if not os.path.exists(metrix_file):
        print("Lỗi: Không tìm thấy training_metrix.json!")
        return
        
    with open(metrix_file, "r", encoding="utf-8") as f:
        metrix = json.load(f)
        
    hp = metrix.get("hyperparameters", {})
    weight_file = metrix.get("weights_file", "xauusd_unified_weights.pth")
    full_weight_path = os.path.join(latest_folder, weight_file)
    
    # 3. Load Dữ Liệu
    features_file = os.path.join(data_path, "final_features_XAUUSD.parquet")
    targets_file = os.path.join(data_path, "target_direction_XAUUSD.parquet")
    
    if not os.path.exists(features_file):
        print("Lỗi: Không tìm thấy file Parquet XAUUSD đặc chế!")
        return
        
    print("Đang Load Dữ Liệu Parquet Lõi...")
    features = pd.read_parquet(features_file)
    targets = pd.read_parquet(targets_file)
    
    # Căn chỉnh khung thời gian (tránh lệch độ dài numpy array)
    combined = features.join(targets, how='inner')
    features = combined[features.columns]
    targets = combined[targets.columns]
    
    # Ép kiểu thời gian
    try:
        features.index = features.index.tz_localize('UTC')
        targets.index = targets.index.tz_localize('UTC')
    except TypeError:
        features = features.tz_convert('UTC')
        targets = targets.tz_convert('UTC')
        
    # Lọc danh sách cột theo data_features nếu có, nếu không lấy tất cả (do Transformer tự bắt shape)
    # Tuy nhiên, nếu shape thay đổi thì model báo lỗi.
    used_features = metrix.get("data_features", [])
    if used_features:
        # Giữ đúng thứ tự và số lượng
        features = features[used_features]
        print(f"Sử dụng màng lọc đúng {len(used_features)} cột từ training_metrix.json.")
    
    num_features = features.shape[1]
    
    # 4. Lọc Dữ Liệu Tháng 10/2025
    start_date = pd.to_datetime('2025-10-01').tz_localize('UTC')
    end_date = pd.to_datetime('2025-10-31').tz_localize('UTC')
    
    mask = (features.index >= start_date) & (features.index <= end_date + pd.Timedelta(days=1))
    f_oct = features[mask]
    t_oct = targets[mask]
    
    print(f"-> Khối lượng Nến T10/2025: {len(f_oct):,} Cây Nến")
    if len(f_oct) < 60:
        print("Không đủ nến để backtest cửa sổ 60 phút.")
        return
        
    # 5. Khai sinh Mô hình & Nạp Bộ Não
    d_model = hp.get('d_model', 128)
    nhead = hp.get('nhead', 4)
    num_encoder_layers = hp.get('num_attn_layers', 2)
    dropout = hp.get('dropout_rate', 0.2)
    
    model = TransformerModel(
        num_features=num_features,
        d_model=d_model,
        nhead=nhead,
        num_layers=num_encoder_layers,
        dropout_rate=dropout
    ).to(device)
    
    print(f"-> Nạp trọng số từ: {full_weight_path}")
    state = torch.load(full_weight_path, map_location=device, weights_only=True)
    
    # === THUẬT TOÁN KẾ THỪA TRỌNG SỐ (TRANSFER LEARNING) ===
    model_dict = model.state_dict()
    pretrained_dict = {}
    for k, v in state.items():
        if k in model_dict and v.shape == model_dict[k].shape:
            pretrained_dict[k] = v
        else:
            print(f"    * Bỏ qua Layer (do lệch Shape/Feature): {k}")
            
    try:
        model_dict.update(pretrained_dict)
        model.load_state_dict(model_dict)
        print("-> Khôi phục thành công các vùng não khớp kích thước, sẵn sàng Backtest!")
    except RuntimeError as e:
        print(f"\n⚠️ LỖI NẠP TRỌNG SỐ: {e}")
        print("\n=> Cảnh báo: Mô hình huấn luyện chưa lưu đợt Epoch nào với kiến trúc Data mới (71 Input)!")
        print("=> Hãy chờ cửa sổ Train chạy xong ít nhất 1 chu kỳ để nó ghi đè file .pth chuẩn rồi mới Backtest được nhé.")
        return
    
    # 6. Đánh giá đa điểm
    thresholds = [0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
    print("\n🔍 QUÉT WIN-RATE CHO THÁNG 10/2025 (UNIFIED MODEL)\n")
    print(f"{'Ngưỡng (Softmax)':<20} | {'Tổng Lệnh Phát Ra':<25} | {'Tỷ Lệ Thắng (Win-Rate)':<20}")
    print("-" * 75)
    
    results = []
    for thr in thresholds:
        correct, total, win_rate = evaluate_model(model, f_oct, t_oct, thr)
        results.append((thr, total, win_rate))
        print(f"Lọc >= {int(thr*100)}% {'':<11} | {total:<25,} | {win_rate:.2f}%")
        
    # Lưu report
    report_text = f"BẢNG REPORT T10/2025 - MODEL: {os.path.basename(latest_folder)}\n"
    for r in results:
        report_text += f"THR {int(r[0]*100)}%: {r[2]:.2f}% (Total: {r[1]})\n"
    with open(os.path.join(base_path, "temp", "backtest_unified_report.txt"), "w", encoding="utf-8") as f:
        f.write(report_text)
    
if __name__ == "__main__":
    main()
