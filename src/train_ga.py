import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import random

# Thiết lập GPU nếu có
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ---------------------------------------------------------
# 1. TỐI ƯU HOÁ RAM: PYTORCH DATASET THÔNG MINH
# ---------------------------------------------------------
class TimeSeriesDataset(Dataset):
    def __init__(self, features, targets, window_size=60):
        self.features = features
        self.targets = targets
        self.window_size = window_size
        
        # Load lên FloatTensor để xử lý siêu tốc
        self.features_tensor = torch.tensor(self.features.values, dtype=torch.float32)
        self.targets_tensor = torch.tensor(self.targets.values, dtype=torch.long)

    def __len__(self):
        # Trừ đi window_size để cửa sổ trượt (sliding window) không văng khỏi mảng
        return len(self.features) - self.window_size

    def __getitem__(self, idx):
        # Cắt động 3D tensor on-the-fly (tiết kiệm hàng GBs RAM)
        x = self.features_tensor[idx : idx + self.window_size]
        y = self.targets_tensor[idx + self.window_size]
        return x, y

# ---------------------------------------------------------
# 2. KIẾN TRÚC MẠNG HYBRID: 1D-CNN kết hợp LSTM
# ---------------------------------------------------------
class CNN_LSTM_Model(nn.Module):
    def __init__(self, num_features, cnn_filters, lstm_units, lstm_layers=2, dropout_rate=0.2):
        super(CNN_LSTM_Model, self).__init__()
        
        # Mạng chập 1 Chiều (Tách nhiễu nến rác)
        self.cnn = nn.Sequential(
            nn.Conv1d(in_channels=num_features, out_channels=cnn_filters, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2)
        )
        
        # Mạng chuỗi dài hạn LSTM
        self.lstm = nn.LSTM(input_size=cnn_filters, hidden_size=lstm_units, 
                            num_layers=lstm_layers, batch_first=True, dropout=dropout_rate if lstm_layers > 1 else 0)
        
        # Lớp Nhận thức cuối cùng dự đoán (Xanh / Đỏ)
        self.fc = nn.Sequential(
            nn.Linear(lstm_units, 32),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(32, 2)  # Output lớp 0 (Down) và 1 (Up)
        )

    def forward(self, x):
        # Neural Torch yêu cầu định dạng chập 1D là (batch, channels, length)
        x = x.permute(0, 2, 1)
        x = self.cnn(x)
        
        # Chuyển về định dạng của LSTM (batch, seq, feature)
        x = x.permute(0, 2, 1)
        lstm_out, _ = self.lstm(x)
        
        # Lấy hidden state của bước cuối cùng (nến T-1) để dự đoán T+5
        last_output = lstm_out[:, -1, :]
        out = self.fc(last_output)
        return out

# ---------------------------------------------------------
# 3. THỬ NGHIỆM ĐỘ THÍCH NGHI (FITNESS SCORE CỦA BỘ GEN DỰ ĐOÁN)
# ---------------------------------------------------------
def evaluate_fitness(chromosome, train_loader, val_loader, num_features):
    # Khui mã Gen di truyền
    window_size, cnn_filters, lstm_units, lstm_layers, dropout_rate, lr = chromosome
    
    # Initialize
    model = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    
    # Huấn luyện siêu tốc 1 Vòng đời (Epoch) đại diện cho sức mạnh sinh học
    model.train()
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(device), batch_y.view(-1).to(device)
        
        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
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
