import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import pandas as pd

from train_ga import CNN_LSTM_Model, TimeSeriesDataset, device

def train_session_model(features, targets, num_features, session_name, start_hour, end_hour):
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
    batch_size = 512
    patience = 15 # Cho Nơ-ron Đáy Bật Thêm 15 Cơ Hội Mới Cắt Đuôi (Tránh Early Stopping quá sớm)
    
    split_idx = int(len(session_features) * 0.8)
    
    # ⚠️ BẢO HIỂM MẠNG NEURON: Tránh Out-of-Bound do Cửa Sổ Trượt 60 nến
    if len(session_features) - split_idx <= window_size:
        split_idx = len(session_features) - window_size - 5
        
    if split_idx <= window_size:
        print(f"⚠️ Dữ liệu siêu cạn kiệt cho {session_name} (chẳng đủ nhét 1 khung {window_size} nến). Rụng kíp Học!")
        return

    train_features = session_features.iloc[:split_idx]
    train_targets = session_targets.iloc[:split_idx]
    val_features = session_features.iloc[split_idx:]
    val_targets = session_targets.iloc[split_idx:]

    print(f"-> Tổng Lượng Nến (Khung M1): {len(train_features)} Train | {len(val_features)} Test")
    
    train_dataset = TimeSeriesDataset(train_features, train_targets, window_size)
    val_dataset = TimeSeriesDataset(val_features, val_targets, window_size)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    model = CNN_LSTM_Model(num_features, cnn_filters=cnn_filters, lstm_layers=lstm_layers, lstm_units=lstm_units, dropout_rate=dropout_rate).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=3, factor=0.5)
    
    best_val_acc = 0.0
    epochs_no_improve = 0
    save_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models"
    os.makedirs(save_path, exist_ok=True)
    model_file = os.path.join(save_path, f"xauusd_{session_name}_weights.pth")
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            
        model.eval()
        correct, total = 0, 0
        val_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
                
        val_acc = correct / total
        print(f"Kỷ nguyên {epoch+1:02d}/{epochs} - Train Loss: {train_loss/len(train_loader):.4f} | Win-Rate: {val_acc*100:.2f}%")
        
        if isinstance(scheduler, optim.lr_scheduler.ReduceLROnPlateau):
            scheduler.step(val_acc)
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            torch.save(model.state_dict(), model_file)
            print(f" 🔥 Đã Khắc Ký Ức Phiên {session_name.upper()} (Đỉnh Mới)!")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f" 🛑 Hội tụ hoàn hảo. Ngừng Sớm (Early Stopping) Phiên {session_name.upper()}.")
                break
                
    print(f"✅ HOÀN TẤT Phiên {session_name.upper()} -> Đã lưu tại: {model_file}")

if __name__ == "__main__":
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    features_path = os.path.join(data_path, "final_features_2d.parquet")
    target_path = os.path.join(data_path, "target_direction.parquet")
    
    if os.path.exists(features_path):
        features = pd.read_parquet(features_path)
        targets = pd.read_parquet(target_path)
        num_features = features.shape[1]
        
        # 1. Phiên Á (Tokyo/Sydney) -> 22:00 - 08:00 UTC
        train_session_model(features, targets, num_features, "asian", 22, 8)
        
        # 2. Phiên Âu (London) -> 08:00 - 13:00 UTC
        train_session_model(features, targets, num_features, "european", 8, 13)
        
        # 3. Phiên Mỹ (New York) -> 13:00 - 22:00 UTC
        train_session_model(features, targets, num_features, "us", 13, 22)
        
    else:
        print("Lỗi: Không tìm thấy dữ liệu Tensor đầu vào!")
