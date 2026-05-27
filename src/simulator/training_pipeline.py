import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np

# ==========================================
# 1. BỘ XỬ LÝ DỮ LIỆU TIME-SERIES (STRICT)
# ==========================================
class QuantTimeSeriesDataset(Dataset):
    def __init__(self, features, labels, returns, seq_len=60):
        """
        features: numpy array (N, num_features)
        labels: numpy array (N,) với giá trị: 0 (HOLD), 1 (BUY), 2 (SELL) 
                Lưu ý: Shift label -1 -> 2 để dùng với PyTorch CrossEntropy.
        returns: numpy array (N,) PnL tuyệt đối của nhãn đó (để đánh trọng số).
        """
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
        self.returns = torch.FloatTensor(returns)
        self.seq_len = seq_len

    def __len__(self):
        return len(self.features) - self.seq_len

    def __getitem__(self, idx):
        # Lấy window thời gian (seq_len, num_features)
        x = self.features[idx : idx + self.seq_len]
        # Lấy nhãn và return tại bước T+1 (cuối window)
        y = self.labels[idx + self.seq_len]
        ret = self.returns[idx + self.seq_len]
        return x, y, ret

# ==========================================
# 2. HÀM MẤT MÁT ASYMMETRIC + RETURN WEIGHTING
# ==========================================
class AsymmetricReturnFocalLoss(nn.Module):
    """
    Focal Loss bất đối xứng:
    - Trừng phạt NẶNG khi model đoán BUY/SELL (1 hoặc 2) nhưng thực tế là HOLD (0). (False Positive)
    - Trừng phạt NHẸ khi model đoán HOLD (0) nhưng thực tế là BUY/SELL. (False Negative - Bảo toàn vốn)
    - Nhân loss với giá trị Return (PnL) để tập trung vào các setup sinh lời lớn.
    """
    def __init__(self, gamma=2.0, fp_penalty=5.0, fn_penalty=0.5):
        super().__init__()
        self.gamma = gamma
        self.fp_penalty = fp_penalty
        self.fn_penalty = fn_penalty

    def forward(self, logits, targets, returns):
        # logits: (Batch, 3), targets: (Batch,)
        probs = F.softmax(logits, dim=1)
        # Lấy prob của class đúng
        target_probs = probs[torch.arange(len(targets)), targets]
        
        # Focal term cơ bản: (1 - pt)^gamma
        focal_weight = (1 - target_probs) ** self.gamma
        
        # Tính Base CE Loss (chưa giảm chiều)
        ce_loss = F.cross_entropy(logits, targets, reduction='none')
        
        # --- Ma trận phạt bất đối xứng ---
        preds = torch.argmax(logits, dim=1)
        penalty_mask = torch.ones_like(targets, dtype=torch.float32)
        
        # Sai lầm chí mạng: Bắn lệnh khi thị trường sideway/nhiễu (Đoán BUY/SELL, thực tế HOLD)
        fp_condition = (targets == 0) & ((preds == 1) | (preds == 2))
        penalty_mask[fp_condition] = self.fp_penalty
        
        # Sai lầm tha thứ được: Lỡ nhịp (Đoán HOLD, thực tế BUY/SELL)
        fn_condition = ((targets == 1) | (targets == 2)) & (preds == 0)
        penalty_mask[fn_condition] = self.fn_penalty

        # Kết hợp: CE * Focal * Asymmetric Penalty * Khối lượng Return (scale từ 1.0 trở lên)
        # Dùng returns (vd: pips lợi nhuận) + 1.0 để tránh làm mất loss ở các lệnh nhỏ
        scaled_returns = (returns.abs() + 1.0) 
        
        final_loss = ce_loss * focal_weight * penalty_mask * scaled_returns
        return final_loss.mean()

# ==========================================
# 3. TRAINING LOOP CHUẨN MỰC
# ==========================================
def train_quant_model(model, train_loader, val_loader, epochs=50, lr=1e-4):
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    criterion = AsymmetricReturnFocalLoss(gamma=2.0, fp_penalty=5.0, fn_penalty=0.5)
    
    # ... Vòng lặp cơ bản ...
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for batch_idx, (x, y, returns) in enumerate(train_loader):
            optimizer.zero_grad()
            
            # x: (Batch, Seq, Features) -> Transform cho hợp format của model
            logits = model(x) 
            
            # Tính loss với Return weighting
            loss = criterion(logits, y, returns)
            
            loss.backward()
            # Gradient clipping là bắt buộc với RNN/Transformer trong chuỗi thời gian
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            total_loss += loss.item()
            
        print(f"Epoch {epoch+1} | Custom Loss: {total_loss/len(train_loader):.4f}")
        # (Ở đây cần hàm đánh giá val_loader chạy logic Simulator)
