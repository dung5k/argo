import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import pandas as pd
import sys
import threading
from pathlib import Path
_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _ROOT not in sys.path: sys.path.insert(0, _ROOT)
from src.orchestration.hf_sync import push_runs

from train_ga import CNN_LSTM_Model, TimeSeriesDataset, FocalLoss, device

def train_session_model(features, targets, num_features, session_name, start_hour, end_hour, run_dir):
    print(f"\n=================================================")
    print(f"🧠 BẮT ĐẦU ÉP KHUNG MODEL PHIÊN: {session_name.upper()} 🧠")
    print(f"=================================================")
    
    # Chuyển Index về UTC để lọc chuẩn mốc giờ Quốc Tế
    features_utc = features.tz_convert('UTC')
    targets_utc = targets.tz_convert('UTC')
    
    if end_hour > start_hour:
        mask = (features_utc.index.hour >= start_hour) & (features_utc.index.hour < end_hour)
    else: # Ví dụ 22h đến 8h sáng hôm sau (Phiên Á)
        mask = (features_utc.index.hour >= start_hour) | (features_utc.index.hour < end_hour)
        
    session_features = features_utc[mask]
    session_targets = targets_utc[mask]
    
    if len(session_features) < 500:
        print(f"⚠️ Data quá ít ({len(session_features)} nến) cho {session_name}. Bỏ qua!")
        return

    import json
    genes_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\best_genes.json"
    if os.path.exists(genes_path):
        with open(genes_path, "r", encoding='utf-8') as f:
            genes = json.load(f)
        window_size = genes.get("window_size", 60)
        cnn_filters = genes.get("cnn_filters", 16)
        lstm_units = genes.get("lstm_units", 128)
        lstm_layers = genes.get("lstm_layers", 2)
        dropout_rate = genes.get("dropout_rate", 0.2)
        lr = genes.get("learning_rate", 0.0005)
        print(f"🧬 [DNA NẠP MỞI] Nạp Cấu Hình Di Truyền Tối Ưu: Window={window_size}, CNN={cnn_filters}, LSTM={lstm_units}x{lstm_layers}")
    else:
        window_size = 60
        cnn_filters = 16
        lstm_layers = 2
        lstm_units = 128
        dropout_rate = 0.2
        lr = 0.0005
        print(f"⚠️ [CẢNH BÁO] Không thấy Trái Tim best_genes.json, dùng Cấu Hình Cứng Bù Đắp!")
    
    epochs = 300 # Chạy Mở Rộng 300 Vòng Máu (Deep Training)
    batch_size = 4096 # GIA TỐC: Đẩy lô dữ liệu lên 4096 nến/Batch (Do tính năng In-Memory GPU)
    patience = 15 # Cho Nơ-ron Đáy Bật Thêm 15 Cơ Hội Mới Cắt Đuôi (Tránh Early Stopping quá sớm)
    
    # 🌟 OOS SPLIT (Chống Overfitting): Học Tháng 1,2 | Thi Tháng 3 🌟
    train_mask = session_features.index < '2026-03-01'
    val_mask = session_features.index >= '2026-03-01'
    
    train_features = session_features[train_mask]
    train_targets = session_targets[train_mask]
    val_features = session_features[val_mask]
    val_targets = session_targets[val_mask]
    
    if len(train_features) <= window_size or len(val_features) <= window_size:
        print(f"⚠️ Dữ liệu siêu cạn kiệt cho {session_name} (chẳng đủ nhét 1 khung {window_size} nến). Rụng kíp Học OOS!")
        return

    print(f"-> Tổng Lượng Nến (Khung M1): {len(train_features)} Train | {len(val_features)} Test")
    
    # ĐỌC METADATA DUAL-STREAM để biết ranh giới tách XAU vs Macro features
    meta_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\feature_meta.json"
    num_xau_features = None
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            import json as _json
            meta = _json.load(f)
            num_xau_features = meta.get("num_xau_features", None)
            print(f"🧬 [DUAL-STREAM] XAU Features: {num_xau_features} | Macro: {num_features - (num_xau_features or 0)}")
    
    model = CNN_LSTM_Model(
        num_features, 
        cnn_filters=cnn_filters, 
        lstm_layers=lstm_layers, 
        lstm_units=lstm_units, 
        dropout_rate=dropout_rate,
        num_xau_features=num_xau_features
    ).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    criterion = FocalLoss(gamma=2.0, label_smoothing=0.1)
    
    global_best_val_loss = float('inf')
    best_val_acc_at_lowest_loss = 0.0
    save_path = run_dir
    os.makedirs(save_path, exist_ok=True)
    model_file = os.path.join(save_path, f"xauusd_{session_name}_weights.pth")
    
    # 🌟 HUẤN LUYỆN TRUYỀN THỐNG (GỘP TOÀN BỘ DATA - TẮT CURRICULUM LÀM NHIỄU) 🌟
    # Tạo Dataset đầy đủ (Tuyết đối Data đã chặn đuôi để không học lấn sang OOS Tháng 3)
    train_dataset = TimeSeriesDataset(train_features, train_targets, window_size)
    val_dataset = TimeSeriesDataset(val_features, val_targets, window_size)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=3, factor=0.5)
    epochs_no_improve = 0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_y = batch_y.view(-1)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        correct, total = 0, 0
        conf_correct, conf_total = 0, 0
        soft_correct, soft_total = 0, 0   # Ngưỡng Mềm Hơn >55% / <45%
        val_loss = 0.0
        with torch.no_grad():
            import torch.nn.functional as F
            for batch_x, batch_y in val_loader:
                batch_y = batch_y.view(-1)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                
                # Mặc định (Tín hiệu Tu mù)
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
                
                probs = F.softmax(outputs.data, dim=1)
                prob_up = probs[:, 1]
                
                # Ngưỡng Khắt Khe >60% / <40%
                buy_mask_60 = prob_up > 0.60
                sell_mask_60 = prob_up < 0.40
                conf_total += buy_mask_60.sum().item() + sell_mask_60.sum().item()
                conf_correct += (batch_y[buy_mask_60] == 1).sum().item() + (batch_y[sell_mask_60] == 0).sum().item()
                
                # Ngưỡng Mềm Hơn >55% / <45%
                buy_mask_55 = prob_up > 0.55
                sell_mask_55 = prob_up < 0.45
                soft_total += buy_mask_55.sum().item() + sell_mask_55.sum().item()
                soft_correct += (batch_y[buy_mask_55] == 1).sum().item() + (batch_y[sell_mask_55] == 0).sum().item()
                
        val_acc = correct / total if total > 0 else 0.0
        conf_acc = conf_correct / conf_total if conf_total > 0 else 0.0
        soft_acc = soft_correct / soft_total if soft_total > 0 else 0.0
        avg_val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
        
        print(f"Kỷ nguyên {epoch+1:02d}/{epochs} - Train Loss: {(train_loss/len(train_loader)) if len(train_loader) > 0 else 0:.4f} | Val Loss: {avg_val_loss:.4f} | WR Thô: {val_acc*100:.1f}% | >55%: {soft_acc*100:.1f}%({soft_total}L) | >60%: {conf_acc*100:.1f}%({conf_total}L)")
        
        if isinstance(scheduler, optim.lr_scheduler.ReduceLROnPlateau):
            scheduler.step(val_acc)
        
        # KHÔNG DÙNG WIN-RATE ĐỂ LỌC TRỌNG SỐ NỮA (DO SẼ BỊ OVERFIT), DÙNG VALIDATION LOSS CHUẨN MỰC
        if avg_val_loss < global_best_val_loss:
            global_best_val_loss = avg_val_loss
            best_val_acc_at_lowest_loss = conf_acc
            epochs_no_improve = 0
            torch.save(model.state_dict(), model_file)
            print(f" 🔥 Đáy Suy Hao Mới Phiên {session_name.upper()} - KHÓA TÍN HIỆU! (Thực Chiến Khắt Khe Đạt: {conf_acc*100:.2f}%)")
            try:
                threading.Thread(target=push_runs, daemon=True).start()
            except Exception as e:
                print(f"  [HF] Bỏ qua sync: {e}")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f" 🛑 Cán mốc Hội Tụ Cứng. Rút lệnh sớm để chống Nhồi Cũ (Overfitting) Phiên {session_name.upper()}!")
                break
                
    print(f"✅ HOÀN TẤT Phiên {session_name.upper()} -> Đã lưu tại: {model_file}")
    
    # GHI REPORT KẾT QUẢ ĐỂ MAI SAU SO SÁNH (EXPERIMENT TRACKING)
    report_file = os.path.join(save_path, f"{session_name}_report.txt")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(f"Phiên Giao Dịch: {session_name.upper()}\n")
        f.write(f"Chiến thuật: HỌC TOÀN BỘ DATA MỎNG BÁM THEO MIN VALIDATION LOSS\n")
        f.write(f"Kiến trúc: DUAL-STREAM (XAU CNN-LSTM + Macro FC Embedder) + BatchNorm + ATR Barrier\n")
        f.write(f"Đáy Validation Loss (Sự kiện lưu Model): {global_best_val_loss:.4f}\n")
        f.write(f"Win-Rate Lọc Ngưỡng >55%: {soft_acc*100:.2f}% ({soft_total} lệnh lọc / {total} tổng)\n")
        f.write(f"Win-Rate Lọc Ngưỡng >60%: {best_val_acc_at_lowest_loss*100:.2f}% ({conf_total} lệnh lọc / {total} tổng)\n")
        f.write(f"Mô hình đã kết thúc trong {epoch+1} vòng (Epochs).\n")
        f.write(f"Đáy Validation Loss (Sự kiện lưu Model): {global_best_val_loss:.4f}\n")
        f.write(f"Tỷ lệ Win-Rate Thực Chiến Khắt Khe (>60% Softmax): {best_val_acc_at_lowest_loss*100:.2f}%\n")
        f.write(f"Mô hình đã kết thúc trong {epoch+1} vòng (Epochs).\n")

if __name__ == "__main__":
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    features_path = os.path.join(data_path, "final_features_2d.parquet")
    target_path = os.path.join(data_path, "target_direction.parquet")
    
    if os.path.exists(features_path):
        features = pd.read_parquet(features_path)
        targets = pd.read_parquet(target_path)
        num_features = features.shape[1]
        
        import concurrent.futures
        import datetime
        print("\n🚀 BẬT CHẾ ĐỘ MULTI-PROCESSING ĐA LUỒNG - NƯỚNG 3 NÃO BỘ Á/ÂU/MỸ SONG SONG...")
        
        # 🌟 KHỞI TẠO TRACKING DIR (TÁCH THƯ MỤC LƯU VẾT) 🌟
        run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        source_name = "BINANCE"
        if any('MT5' in col for col in features.columns):
            source_name = "MT5"
        
        run_name = f"run_{run_timestamp}_{source_name}"
        run_dir = os.path.join(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs", run_name)
        os.makedirs(run_dir, exist_ok=True)
        print(f"📁 Tự động tạo Hồ Sơ Quản Trị Trọng Số tại: {run_name}")
        
        sessions = [
            ("asian", 22, 8),
            ("european", 8, 13),
            ("us", 13, 22)
        ]
        
        # THÁO BỎ THREADPOOL (TRÁNH XUNG ĐỘT PYTORCH CPU CORES)
        # Chạy tuần tự để PyTorch được gánh trọn vẹn sức mạnh 100% CPU vào từng Mẻ nướng
        for session_name, start_hour, end_hour in sessions:
            train_session_model(features, targets, num_features, session_name, start_hour, end_hour, run_dir)
                
        print("\n🏆 ĐÃ HOÀN TẤT LẦN LƯỢT ĐÚC NÃO 3 PHIÊN CÙNG KÈM REPORT! MỜI SẾP DÙNG! 🏆")
        try:
            push_runs()
        except:
            pass
        
    else:
        print("Lỗi: Không tìm thấy dữ liệu Tensor đầu vào!")
