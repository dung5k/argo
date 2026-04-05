import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import random

# Thiết lập GPU nếu có
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ---------------------------------------------------------
# FOCAL LOSS: Phạt nặng những nến khó đoán, bỏ qua sideways đơn giản
# ---------------------------------------------------------
class FocalLoss(nn.Module):
    """
    Focal Loss = -(1 - pt)^gamma * log(pt)
    gamma=2: tập trung vào những mẫu khó (nến đảo chiều)
    alpha=None: không có class weighting (dùng label_smoothing riêng)
    """
    def __init__(self, gamma=2.0, label_smoothing=0.1, reduction='mean'):
        super().__init__()
        self.gamma = gamma
        self.label_smoothing = label_smoothing
        self.reduction = reduction
        self.ce = nn.CrossEntropyLoss(label_smoothing=label_smoothing, reduction='none')

    def forward(self, inputs, targets):
        ce_loss = self.ce(inputs, targets)
        pt = torch.exp(-ce_loss)  # pt = xác suất đúng của từng mẫu
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean() if self.reduction == 'mean' else focal_loss.sum()


# ---------------------------------------------------------
# 1. TỐI ƯU HOÁ RAM: PYTORCH DATASET THÔNG MINH
# ---------------------------------------------------------
class TimeSeriesDataset(Dataset):
    def __init__(self, features, targets, window_size=60):
        self.targets = targets
        self.window_size = window_size
        
        # Lọc ngang: Lọc bỏ Cửa sổ chứa quá 15% Nến Ma
        self.valid_indices = []
        if 'is_imputed_flag' in features.columns:
            flags_array = features['is_imputed_flag'].values
            
            for i in range(len(features) - window_size):
                window_flags_sum = sum(flags_array[i : i + window_size])
                # Nếu số Nến ma <= 15% tổng Nến trong Cửa sổ (vd 9/60)
                if window_flags_sum <= (0.15 * window_size):
                    self.valid_indices.append(i)
                    
            # Tách cờ ra khỏi feature để không đưa vào làm nhiễu Input Tensor
            # Hoặc Giữ lại? Giữ lại giúp AI nhận biết nến ảo. Rất Tốt! Ta Giữ Lại.
        else:
            self.valid_indices = list(range(len(features) - window_size))
            
        print(f"-> [DATASET] Khởi tạo Cửa sổ Trượt: Tổng {len(features)-window_size:,} Mẫu. Loại bỏ {len(features) - window_size - len(self.valid_indices):,} Mẫu Rách (Nến Ma > 15%).")
        
        self.features = features
        # GIA TỐC VŨ TRỤ (IN-MEMORY GPU DATASET): Đẩy thẳng toàn bộ Data vào VRAM!
        self.features_tensor = torch.tensor(self.features.values, dtype=torch.float32).to(device)
        self.targets_tensor = torch.tensor(self.targets.values, dtype=torch.long).to(device)

    def __len__(self):
        return len(self.valid_indices)

    def __getitem__(self, raw_idx):
        idx = self.valid_indices[raw_idx]
        # Cắt động 3D tensor on-the-fly (tiết kiệm hàng GBs RAM)
        x = self.features_tensor[idx : idx + self.window_size]
        # Xài hàm Trừ 1 (-1) Khôi phục sự đồng bộ T+10: Dự đoán đúng ngay Tương lai của Cây nến Mới nhất (B-1)
        y = self.targets_tensor[idx + self.window_size - 1]
        return x, y

# ---------------------------------------------------------
# 2. KIẾN TRÚC MẠNG HYBRID DUAL-STREAM (CN ĐÃ NÂNG CẤP)
#    Luồng 1: XAUUSD Technical (LSTM sâu)
#    Luồng 2: Macro G7+Crypto (FC Embedder)
#    Merge -> Quyết định
# ---------------------------------------------------------
class CNN_LSTM_Model(nn.Module):
    def __init__(self, num_features, cnn_filters, lstm_units, lstm_layers=1, dropout_rate=0.2, num_xau_features=None):
        super(CNN_LSTM_Model, self).__init__()
        
        # Chia Input thành 2 luồng: XAU Technical và Macro
        # num_xau_features: số features thuộc XAU (phần đầu của tensor)
        # Nếu không truyền vào thì giả định 1/3 là XAU, 2/3 là Macro
        self.num_xau_features = num_xau_features if num_xau_features else max(1, num_features // 3)
        self.num_macro_features = num_features - self.num_xau_features
        
        # ============= LUỒNG 1: XAU TECHNICAL (CNN + LSTM) =============
        # [FIX 1]: Dùng stride=2 thay MaxPool để giữ Thứ Tự Thời Gian Tuyến Tính
        self.xau_cnn = nn.Sequential(
            nn.Conv1d(in_channels=self.num_xau_features, out_channels=cnn_filters, 
                      kernel_size=3, padding=1, stride=2),  # Stride thay MaxPool
            nn.ReLU(),
            # [FIX 2]: BatchNorm sau CNN để ổn định Gradient
            nn.BatchNorm1d(cnn_filters),
            # Lớp CNN thứ 2 để bắt Pattern phức tạp hơn (Double Convolution)
            nn.Conv1d(in_channels=cnn_filters, out_channels=cnn_filters * 2,
                      kernel_size=3, padding=1),
            nn.ReLU(),
            nn.BatchNorm1d(cnn_filters * 2),
            nn.Dropout(dropout_rate)
        )
        
        # LSTM bắt Pattern Chuỗi Dài Hạn
        self.xau_lstm = nn.LSTM(
            input_size=cnn_filters * 2, 
            hidden_size=lstm_units, 
            num_layers=lstm_layers, 
            batch_first=True, 
            dropout=dropout_rate if lstm_layers > 1 else 0
        )
        
        # ============= LUỒNG 2: MACRO EMBEDDER (FC nhanh) =============
        # Nhúng tín hiệu Macro vào không gian thấp chiều (Low-dim Macro Signal)
        # [FIX: Ý tưởng 2] Tách biệt, không lẫn lộn Macro vào LSTM của XAU
        self.macro_fc = nn.Sequential(
            nn.Linear(self.num_macro_features, lstm_units // 2),
            nn.ReLU(),
            nn.BatchNorm1d(lstm_units // 2),
            nn.Dropout(dropout_rate),
            nn.Linear(lstm_units // 2, lstm_units // 4),
            nn.ReLU()
        )
        
        # ============= TỔNG HỢP (MERGE DECISION HEAD) =============
        # Kết hợp tín hiệu kỹ thuật XAU + Ký hiệu Vĩ Mô Macro
        merged_size = lstm_units + lstm_units // 4
        self.decision_head = nn.Sequential(
            nn.Linear(merged_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(64, 2)  # Output: 0 (Down) và 1 (Up)
        )

    def forward(self, x):
        # Tách input thành 2 luồng theo chiều Feature
        xau_feats = x[:, :, :self.num_xau_features]      # Đặc trưng XAUUSD Kỹ Thuật
        macro_feats = x[:, -1, self.num_xau_features:]   # Đặc trưng Macro (Chỉ cần Thời điểm Cuối)
        
        # --- LUỒNG 1: XAU TECHNICAL STREAM ---
        # CNN yêu cầu (batch, channels, length)
        xau_t = xau_feats.permute(0, 2, 1)
        xau_t = self.xau_cnn(xau_t)
        # LSTM yêu cầu (batch, seq, feature)
        xau_t = xau_t.permute(0, 2, 1)
        xau_out, _ = self.xau_lstm(xau_t)
        xau_signal = xau_out[:, -1, :]  # Trích Hidden state cuối
        
        # --- LUỒNG 2: MACRO SIGNAL STREAM ---
        macro_signal = self.macro_fc(macro_feats)
        
        # --- MERGE: Ghép 2 Tín Hiệu ---
        merged = torch.cat([xau_signal, macro_signal], dim=1)
        out = self.decision_head(merged)
        return out

# ---------------------------------------------------------
# [#1] KIẾN TRÚC TRANSFORMER (THAY THẾ LSTM BẰNG ATTENTION)
#   - Multi-Head Self-Attention: Nhìn TẤT CẢ 30 nến cùng lúc
#   - Positional Encoding: Dạy AI biết nến nào trước nến nào
#   - Tránh Vanishing Gradient của LSTM trên chuỗi dài
#   - Vẫn giữ Dual-Stream: XAU → Transformer, Macro → FC
# ---------------------------------------------------------
class PositionalEncoding(nn.Module):
    """Mã hóa vị trí Sinusoidal để Transformer hiểu thứ tự nến"""
    def __init__(self, d_model, max_len=200, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:, :x.size(1), :]
        return self.dropout(x)

class TransformerModel(nn.Module):
    def __init__(self, num_features, d_model=64, nhead=4, num_layers=2, 
                 dropout_rate=0.2, num_xau_features=None):
        super(TransformerModel, self).__init__()
        
        self.num_xau_features = num_xau_features if num_xau_features else max(1, num_features // 3)
        self.num_macro_features = num_features - self.num_xau_features
        
        # Đảm bảo d_model chia hết cho nhead
        if d_model % nhead != 0:
            d_model = (d_model // nhead) * nhead
        self.d_model = d_model
        
        # === LUỒNG 1: XAU TRANSFORMER STREAM ===
        self.xau_input_proj = nn.Linear(self.num_xau_features, d_model)
        self.xau_pos_enc = PositionalEncoding(d_model, dropout=dropout_rate)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, 
            dim_feedforward=d_model * 4,
            dropout=dropout_rate, batch_first=True, norm_first=True  # Pre-LN: ổn định hơn
        )
        self.xau_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers, enable_nested_tensor=False)
        
        # === LUỒNG 2: MACRO FC EMBEDDER ===
        macro_hidden = max(16, d_model // 4)
        self.macro_fc = nn.Sequential(
            nn.Linear(self.num_macro_features, d_model // 2),
            nn.GELU(),
            nn.LayerNorm(d_model // 2),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model // 2, macro_hidden),
            nn.GELU()
        )
        
        # === MERGE + DECISION HEAD ===
        merged_size = d_model + macro_hidden
        self.decision_head = nn.Sequential(
            nn.LayerNorm(merged_size),
            nn.Linear(merged_size, d_model),
            nn.GELU(),
            nn.Dropout(dropout_rate),
            nn.Linear(d_model, 2)
        )

    def forward(self, x):
        xau_feats = x[:, :, :self.num_xau_features]
        macro_feats = x[:, -1, self.num_xau_features:]
        
        # XAU TRANSFORMER: Project → PositionalEncode → Self-Attention → Lấy token cuối
        xau_t = self.xau_input_proj(xau_feats)
        xau_t = self.xau_pos_enc(xau_t)
        xau_t = self.xau_transformer(xau_t)
        xau_signal = xau_t[:, -1, :]  # Token cuối = tín hiệu HIỆN TẠI
        
        # MACRO EMBEDDER
        macro_signal = self.macro_fc(macro_feats)
        
        # MERGE
        merged = torch.cat([xau_signal, macro_signal], dim=1)
        return self.decision_head(merged)


# ---------------------------------------------------------
def evaluate_fitness(chromosome, train_loader, val_loader, num_features):
    # Khui mã Gen di truyền
    window_size, cnn_filters, lstm_units, lstm_layers, dropout_rate, lr = chromosome
    
    # Initialize
    model = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-3)
    criterion = FocalLoss(gamma=2.0, label_smoothing=0.1)
    
    # Huấn luyện siêu tốc 1 Vòng đời (Epoch) đại diện cho sức mạnh sinh học
    model.train()
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
        
        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
    # Testing Score chéo (Chống thiên vị Look-ahead)
    model.eval()
    correct, total = 0, 0
    with torch.no_grad():
        for batch_x, batch_y in val_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
            outputs = model(batch_x)
            _, predicted = torch.max(outputs.data, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
            
    return correct / total # Accuracy (Win-rate ratio)

# ---------------------------------------------------------
# 4. GIẢI THUẬT DI TRUYỀN (Tiến hoá Nhân tạo AI)
# ---------------------------------------------------------
def genetic_algorithm(features, targets, num_features):
    print(f"\n🚀 TRUNG TÂM TIẾN HOÁ GENETIC (CHẠY QUA BẰNG {device}) 🚀")
    
    # Bể gen tham số cho đột biến và lai tạo (Gene Space)
    window_genes = [15, 30, 60, 90]
    cnn_genes = [16, 32, 64]
    lstm_genes = [32, 64, 128]
    layers_genes = [1, 2, 3]
    dropout_genes = [0.1, 0.2, 0.3, 0.4]
    lr_genes = [0.001, 0.005, 0.0005]
    
    # Cày cuốc 8 quần thể trên 20 vòng đời (Generations) để đánh thức Thần thú cuối cùng
    population_size = 8
    generations = 20
    
    # Khởi tạo hạt giống ngẫu nhiên (F1)
    population = []
    for _ in range(population_size):
        chrom = [random.choice(window_genes), random.choice(cnn_genes), 
                 random.choice(lstm_genes), random.choice(layers_genes),
                 random.choice(dropout_genes), random.choice(lr_genes)]
        population.append(chrom)
        
    # Cắt ngang Tập kiểm thử Training (80%) và Validation xác nhận (20%)
    split_idx = int(len(features) * 0.8)
    
    best_overall_score = 0
    best_overall_chrom = None
    
    for gen in range(generations):
        print(f"\n--- Mùa Tiến hoá thứ {gen + 1}/{generations} ---")
        fitness_scores = []
        
        for idx, chrom in enumerate(population):
            window_size = chrom[0]
            
            # Cắt DataLoader riêng theo kích thước gen Window_Size
            train_dataset = TimeSeriesDataset(features.iloc[:split_idx], targets.iloc[:split_idx], window_size)
            val_dataset = TimeSeriesDataset(features.iloc[split_idx:], targets.iloc[split_idx:], window_size)
            
            # Batch size siêu lớn 512 do DataLoader tiết kiệm RAM khủng khiếp
            train_loader = DataLoader(train_dataset, batch_size=512, shuffle=False)
            val_loader = DataLoader(val_dataset, batch_size=512, shuffle=False)
            
            score = evaluate_fitness(chrom, train_loader, val_loader, num_features)
            fitness_scores.append(score)
            
            print(f"🧬 Sinh vật {idx+1} {chrom} -> Win-Rate ảo: {score*100:.2f}%")
            
            if score > best_overall_score:
                best_overall_score = score
                best_overall_chrom = chrom
                
        # Lai tạo và Đột biến cho thế hệ con
        sorted_indices = np.argsort(fitness_scores)[::-1]
        parent1 = population[sorted_indices[0]] # Cha Mẹ khoẻ nhất
        parent2 = population[sorted_indices[1]]
        
        new_population = [parent1, parent2] # Mẫu quốc nguyên vẹn (Elitism)
        
        while len(new_population) < population_size:
            # Trao đổi gen ngẫu nhiên từng cặp NST
            child = [parent1[i] if random.random() > 0.5 else parent2[i] for i in range(6)]
            
            # Phóng xạ Đột biến (Mutation 25%)
            if random.random() < 0.25:
                mutate_pos = random.randint(0, 5)
                if mutate_pos == 0: child[0] = random.choice(window_genes)
                elif mutate_pos == 1: child[1] = random.choice(cnn_genes)
                elif mutate_pos == 2: child[2] = random.choice(lstm_genes)
                elif mutate_pos == 3: child[3] = random.choice(layers_genes)
                elif mutate_pos == 4: child[4] = random.choice(dropout_genes)
                elif mutate_pos == 5: child[5] = random.choice(lr_genes)
                
            new_population.append(child)
        population = new_population
        
    print("\n" + "="*50)
    print(f"💰 VỊ VUA CỦA DỰ BÁO XAUUSD (BEST GENES):")
    print(f"1. Window Size (Số lượng nến để nhìn lại): {best_overall_chrom[0]} phút")
    print(f"2. Nơ-ron Lọc nhiễu CNN: {best_overall_chrom[1]} filters")
    print(f"3. Cấu trúc bộ nhớ LSTM: {best_overall_chrom[3]} layers x {best_overall_chrom[2]} units")
    print(f"4. Hệ số rụng rỗng (Dropout Rate): {best_overall_chrom[4]}")
    print(f"5. Tốc độ nạp (Learning Rate): {best_overall_chrom[5]}")
    print(f">> Win-Rate Chính xác nhất (chưa Train sâu): {best_overall_score*100:.2f}%")
    print("="*50)
    
    # KẾT XUẤT BỘ GEN VIP RA FILE CHO TRAIN_FINAL NẠP VÀO
    import json
    best_genes_dict = {
        "window_size": best_overall_chrom[0],
        "cnn_filters": best_overall_chrom[1],
        "lstm_units": best_overall_chrom[2],
        "lstm_layers": best_overall_chrom[3],
        "dropout_rate": best_overall_chrom[4],
        "learning_rate": best_overall_chrom[5]
    }
    genes_path = os.path.join(data_path, "best_genes.json")
    with open(genes_path, "w", encoding='utf-8') as f:
        json.dump(best_genes_dict, f, indent=4)
        
    print(f"\n✅ ĐÃ LƯU BỘ GEN THẦN THÁNH VÀO: {genes_path}")
    print(f"👉 Hãy chuyển sang chạy File 'train_final.py' để Đào tạo Trí Tuệ bằng bộ Gen này!")

if __name__ == "__main__":
    data_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data"
    features_path = os.path.join(data_path, "final_features_2d.parquet")
    target_path = os.path.join(data_path, "target_direction.parquet")
    
    if os.path.exists(features_path):
        features = pd.read_parquet(features_path)
        targets = pd.read_parquet(target_path)
        
        genetic_algorithm(features, targets, num_features=features.shape[1])
    else:
        print("Lỗi: Không tìm thấy dữ liệu Tensor. Chạy module Tiền Xử Lý (Feature Engineering) trước!")
