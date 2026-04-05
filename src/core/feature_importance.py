import os
import sys
import json
import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader

# Handle utf-8 encoding for windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import TransformerModel
from train_ga import TransformerModel, TimeSeriesDataset, device

def main():
    print("⏳ Đang khởi tạo bộ máy đánh giá Tầm Quan Trọng (Permutation Importance)...")
    
    # 1. Đọc config & chuẩn bị Data Path
    target_prefix = "XAUUSD"
            
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    features_path = os.path.join(data_path, f"final_features_{target_prefix}.parquet")
    target_path = os.path.join(data_path, f"target_direction_{target_prefix}.parquet")
    
    if not os.path.exists(features_path):
        print(f"❌ Không tìm thấy {features_path}")
        return
        
    features = pd.read_parquet(features_path)
    targets = pd.read_parquet(target_path)
    
    # Rút lại chỉ dùng khoảng 5000 nến Validate cuối cùng (tương đương ~3-4 ngày) để test nhanh
    val_features = features.iloc[-5000:].copy()
    val_targets = targets.iloc[-5000:].copy()
    
    num_features = features.shape[1]
    feature_names = features.columns.tolist()
    
    # 2. Đọc Kiến trúc Model & Meta
    genes_path = os.path.join(data_path, "best_genes.json")
    if os.path.exists(genes_path):
        with open(genes_path, "r", encoding="utf-8") as f:
            genes = json.load(f)
        window_size = genes.get("window_size", 30)
        d_model = genes.get("lstm_units", 128)
        num_attn_layers = genes.get("lstm_layers", 2)
    else:
        window_size, d_model, num_attn_layers = 30, 128, 2
        
    meta_path = os.path.join(data_path, f"feature_meta_{target_prefix}.json")
    num_xau_features = None
    target_name = target_prefix.lower().replace("_", "")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            num_xau_features = meta.get("num_xau_features", None)
            target_name = meta.get("target_prefix", target_prefix).lower().replace("_", "")
            
    # 3. Khởi tạo Model & Tìm Checkpoint Mới nhất
    model = TransformerModel(
        num_features=num_features, d_model=d_model, nhead=4,
        num_layers=num_attn_layers, dropout_rate=0.0,
        num_xau_features=num_xau_features
    ).to(device)
    
    from pathlib import Path
    runs_base = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs"
    checkpoints = sorted(Path(runs_base).glob(f"**/{target_name}_unified_weights.pth"), key=os.path.getmtime, reverse=True)
    
    if not checkpoints:
        print("❌ Không tìm thấy file trọng số.")
        return
        
    latest_ckpt = checkpoints[0]
    print(f"✅ Đang nạp não bộ từ: {latest_ckpt}")
    model.load_state_dict(torch.load(str(latest_ckpt), map_location=device))
    model.eval()
    
    # 4. Helper Function Tính Loss Của 1 Tập Dữ liệu
    criterion = nn.CrossEntropyLoss()
    
    def evaluate_loss(feat_df):
        dataset = TimeSeriesDataset(feat_df, val_targets, window_size)
        loader = DataLoader(dataset, batch_size=512, shuffle=False)
        total_loss = 0.0
        with torch.no_grad():
            for batch_x, batch_y in loader:
                batch_y = batch_y.view(-1)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                total_loss += loss.item() * batch_x.size(0)
        return total_loss / len(dataset)
        
    # Bước nhảy 1: Đo Baseline Loss (Giá trị tham chiếu gốc)
    baseline_loss = evaluate_loss(val_features)
    print(f"📊 Baseline Loss (Chuẩn): {baseline_loss:.5f}")
    
    # Bước nhảy 2: Xáo trộn (Permutation) từng cột để xem Hậu quả
    print("\n🔍 Đang tra tấn (Shuffling) từng mã dữ liệu. Vui lòng đợi...")
    importance_scores = []
    
    # Nhóm biến gốc (Symbol gốc) để report đỡ dài
    # Ví dụ cột: 'EURUSD_close', 'EURUSD_volume' -> nhóm thành 'EURUSD'
    symbol_groups = {}
    for col in feature_names:
        base_sym = col.split('_')[0]
        if base_sym not in symbol_groups:
            symbol_groups[base_sym] = []
        symbol_groups[base_sym].append(col)
        
    # Tính Importance theo Nhóm Symbol (Thay vì từng cột lắt nhắt sẽ mất thời gian & khó nhìn)
    for group_name, cols in symbol_groups.items():
        if group_name == 'is': continue # bỏ qua is_imputed_flag
        
        # Băm nát dữ liệu của toàn bộ nhóm cols
        shuffled_features = val_features.copy()
        
        # Shuffle các dòng của nhóm này
        for col in cols:
            shuffled_features[col] = np.random.permutation(shuffled_features[col].values)
            
        shuffled_loss = evaluate_loss(shuffled_features)
        
        # Điểm ảnh hưởng (Importance) = Độ thiệt hại gây ra khi bị phá
        # Loss tăng càng xịt -> Mã này càng Đẹp/Quan Trọng
        # Loss không đổi hoặc âm -> Mã này Vô dụng / Nhiễu
        importance = shuffled_loss - baseline_loss
        importance_scores.append((group_name, len(cols), importance))
        print(f"   [+] Độ phụ thuộc vào {group_name:<10}: {importance:+.5f}")
        
    # 5. Phân Tích Kêt quả
    importance_scores.sort(key=lambda x: x[2], reverse=True)
    
    print("\n" + "="*50)
    print("🏆 BẢNG XẾP HẠNG TẦM QUAN TRỌNG CỦA CÁC MÃ DỮ LIỆU")
    print("="*50)
    print(f"{'Mã (Tài Sản)':<15} | {'Số Cột':<7} | {'Trạng Thái Điểm Số_Score'}")
    print("-" * 50)
    
    report = []
    for sym, count, score in importance_scores:
        status = "🌟 SIÊU QUAN TRỌNG" if score > 0.005 else ("✅ HỮU ÍCH" if score > 0.001 else ("🟨 BÌNH THƯỜNG" if score > 0 else "🗑️ VÔ DỤNG (RÁC)"))
        line = f"{sym:<15} | {count:<7} | {score:+.5f} -> {status}"
        print(line)
        report.append({"symbol": sym, "score": float(score), "status": status})
        
    with open("importance_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    print("\n✅ Hoàn tất bài test! Danh sách Rác đã được lộ diện.")

if __name__ == "__main__":
    main()
