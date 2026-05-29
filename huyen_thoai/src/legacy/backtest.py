import os
import torch
import pandas as pd
from torch.utils.data import DataLoader
from train_ga import CNN_LSTM_Model, TimeSeriesDataset, device

def evaluate_session(model, features, targets, session_name, window_size=60, threshold=0.85):
    if len(features) <= window_size:
        print(f"[{session_name.upper()}] -> Quá ít nến để nạp Cửa Sổ 60")
        return 0, 0
    
    dataset = TimeSeriesDataset(features, targets, window_size)
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
    print(f"💎 CHUYÊN GIA [{session_name.upper()}] -> Win-Rate Thực Chiến: {win_rate:.2f}% (Đúng {correct}/{total} Tín Hiệu)")
    return correct, total

def main():
    print(f"\n=================================================")
    print(f"🚀 ENGINE BACKTEST ĐỘC LẬP - KIỂM KIÊM MODEL THÁNG 3/2026 🚀")
    print(f"=================================================\n")
    
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    model_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models"
    
    features_file = os.path.join(data_path, "final_features_2d.parquet")
    targets_file = os.path.join(data_path, "target_direction.parquet")
    
    if not os.path.exists(features_file):
        print("Lỗi: Không tìm thấy Bộ Dữ liệu Tensor!")
        return
        
    print("Đang Load 24MB Dữ Liệu Parquet Lõi...")
    features = pd.read_parquet(features_file)
    targets = pd.read_parquet(targets_file)
    num_features = features.shape[1]
    
    # Ép kiểu thời gian sang UTC nếu cần (do MT5 Crawler Data đã chuẩn hóa về UTC+0 vật lý)
    try:
        features.index = features.index.tz_localize('UTC')
        targets.index = targets.index.tz_localize('UTC')
    except TypeError:
        features = features.tz_convert('UTC')
        targets = targets.tz_convert('UTC')
        
    # CẮT ĐỘC LẬP DỮ LIỆU CỦA ĐÚNG THÁNG 03/2026
    start_date = pd.to_datetime('2026-03-01').tz_localize('UTC')
    end_date = pd.to_datetime('2026-03-31').tz_localize('UTC')
    
    mask_march = (features.index >= start_date) & (features.index <= end_date + pd.Timedelta(days=1))
    f_march = features[mask_march]
    t_march = targets[mask_march]
    
    print(f"-> Thể tích Tháng 03/2026: {len(f_march):,} Cây Nến (Đều Tăm Tắp UTC+0)")
    
    if len(f_march) == 0:
        print("Không có nến nào trong mốc T3/2026. Có thể chưa cào tới?")
        return
        
    # Chuẩn bị chia theo 3 múi giờ Phiên Y Hệt Hàm Train (Á, Âu, Mỹ)
    mask_asian = (f_march.index.hour >= 22) | (f_march.index.hour < 8)
    mask_euro = (f_march.index.hour >= 8) & (f_march.index.hour < 13)
    mask_us = (f_march.index.hour >= 13) & (f_march.index.hour < 22)
    
    # Load 3 Bộ Não PyTorch
    print("Kích Hoạt Liên Kết Não 3 Chuyên Gia...\n")
    cnn_filters = 16
    lstm_layers = 2
    lstm_units = 128
    dropout_rate = 0.2
    
    model_asian = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
    model_asian.load_state_dict(torch.load(os.path.join(model_path, "xauusd_asian_weights.pth")))
    
    model_euro = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
    model_euro.load_state_dict(torch.load(os.path.join(model_path, "xauusd_european_weights.pth")))
    
    model_us = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
    model_us.load_state_dict(torch.load(os.path.join(model_path, "xauusd_us_weights.pth")))
    
    # Tính Cường Độ Win-rate Đa Ngưỡng (Multi-Threshold Scanning)
    thresholds = [0.55, 0.65, 0.70, 0.75, 0.80]
    
    print("\n🔍 KẾT QUẢ ĐỘT PHÁ WIN-RATE THEO NGƯỠNG SOFTMAX (PHƯƠNG ÁN 1)\n")
    print(f"{'Ngưỡng (Threshold)':<20} | {'Tổng Số Lệnh (Trades)':<25} | {'Tỷ Lệ Thắng (Win-Rate)':<20}")
    print("-" * 75)
    
    results = []
    
    for thr in thresholds:
        c_asian, t_asian = evaluate_session(model_asian, f_march[mask_asian], t_march[mask_asian], "asian", threshold=thr)
        c_euro, t_euro  = evaluate_session(model_euro, f_march[mask_euro], t_march[mask_euro], "european", threshold=thr)
        c_us, t_us    = evaluate_session(model_us, f_march[mask_us], t_march[mask_us], "us", threshold=thr)
        
        total_correct = c_asian + c_euro + c_us
        total_signals = t_asian + t_euro + t_us
        overall_win_rate = (total_correct / total_signals) * 100 if total_signals > 0 else 0
        
        results.append((thr, total_signals, overall_win_rate))
    
    # Xoá bớt output rác từ `evaluate_session` bằng cách sửa hàm in trong file hoặc in tổng kết luôn
    # Ghi File Report
    report_text = f"🌟 BẢNG TỔNG KẾT CHIẾN DỊCH THÁNG 3/2026 🌟\n"
    report_text += f"{'SOFTMAX THRESHOLD':<20} | {'SỐ LƯỢNG LỆNH VÀO':<25} | {'TỶ LỆ THẮNG (WIN-RATE)':<20}\n"
    report_text += "-" * 75 + "\n"
    for r in results:
        report_text += f"Lọc Tín Hiệu > {int(r[0]*100)}%   | {r[1]:<25,} | {r[2]:.2f}%\n"
        
    print(report_text)
    with open("backtest_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

if __name__ == "__main__":
    main()
