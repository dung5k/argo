import pytest
import torch
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import sys
import os

# Add project root to sys path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.training_v3.model_v3 import AAMT_Model
from src.training_v3.loss_v3 import AAMT_JointLoss
from src.training_v3.train_v3 import train_warmup_phase, train_finetuning_phase

def test_training_phases_overfit():
    """Kiểm chứng xem Model có thể học và giảm Overfit Loss trên 1 batch nhỏ không"""
    torch.manual_seed(42)
    device = torch.device('cpu')
    
    # Thiết lập Mạng nhỏ thôi để test cho lẹ (d_model=32, layers=2)
    model = AAMT_Model(input_dim=15, seq_len=60, d_model=32, nhead=4, num_layers=2, num_classes=3)
    criterion = AAMT_JointLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01) # Learning rate to bự để ép rớt loss nhanh
    
    # Giả lập 4 Mẫu Dữ liệu (Batch Size = 4)
    x_dummy = torch.randn(4, 60, 15)
    y_dummy = torch.tensor([0, 1, 2, 1], dtype=torch.long)
    
    dataset = TensorDataset(x_dummy, y_dummy)
    loader = DataLoader(dataset, batch_size=4)
    
    # ==========================================
    # TEST 1: Warm-up Phase (Chỉ bật MSE)
    # ==========================================
    # Lấy Loss của Bước khởi điểm
    model.eval()
    with torch.no_grad():
        recon_start, _, _ = model(x_dummy)
        loss_start, l_recon_start, _ = criterion(recon_start, x_dummy, torch.zeros(4,3), y_dummy)
        
    model = train_warmup_phase(model, loader, criterion, optimizer, device, epochs=10)
    
    model.eval()
    with torch.no_grad():
        recon_end, _, _ = model(x_dummy)
        loss_end, l_recon_end, _ = criterion(recon_end, x_dummy, torch.zeros(4,3), y_dummy)
        
    assert l_recon_end < l_recon_start, "Lỗi! Mạng KHÔNG TỰ HỌC ĐƯỢC qua Warm-up. MSE không giảm!"
    
    # ==========================================
    # TEST 2: Fine-Tuning Phase (Bật cả CE + MSE)
    # ==========================================
    optimizer = optim.Adam(model.parameters(), lr=0.01) # Reset optimizer
    
    model.eval()
    with torch.no_grad():
        _, logits_start, _ = model(x_dummy)
        _, _, l_class_start = criterion(recon_end, x_dummy, logits_start, y_dummy)
        
    model = train_finetuning_phase(model, loader, criterion, optimizer, device, epochs=15)
    
    model.eval()
    with torch.no_grad():
        _, logits_end, _ = model(x_dummy)
        _, _, l_class_end = criterion(recon_end, x_dummy, logits_end, y_dummy)
        
    assert l_class_end < l_class_start, "Lỗi! Mạng KHÔNG TỰ HỌC ĐƯỢC qua Fine-tuning. Cross-Entropy không giảm!"
