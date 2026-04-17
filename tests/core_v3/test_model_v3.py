import torch
import sys
import os
import pytest

# Add project root to sys path
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.training_v3.model_v3 import AAMT_Model

def test_aamt_model_shapes():
    """Nhét 1 dummy data vào mô hình để kiểm chứng tensor shapes đầu ra không bị vỡ"""
    
    # Khai báo các siêu tham số như mô phỏng
    batch_size = 4
    seq_len = 60
    input_dim = 15
    d_model = 128
    num_classes = 3
    
    # Sinh ma trận đầu vào ngẫu nhiên
    x = torch.randn(batch_size, seq_len, input_dim)
    
    # Khởi tạo mô hình
    try:
        model = AAMT_Model(
            input_dim=input_dim,
            seq_len=seq_len,
            d_model=d_model,
            num_classes=num_classes
        )
    except Exception as e:
        pytest.fail(f"Lỗi khởi tạo Model: {e}")
        
    # Chạy lan truyền xuôi (Forward pass)
    try:
        reconstructed, logits, latent_vector = model(x)
    except Exception as e:
        pytest.fail(f"Lỗi trong quá trình Forward pass: {e}")
        
    # Bắt đầu Check Shape
    
    # 1. Output của nhánh Reconstruct phải hệt như kích thước Origin Input
    assert reconstructed.shape == (batch_size, seq_len, input_dim), \
        f"Reconstruct shape rách: Kỳ vọng {(batch_size, seq_len, input_dim)}, Nhận {reconstructed.shape}"
        
    # 2. Output của nhánh Classifier phân phải khớp với số nhãn (num_classes)
    assert logits.shape == (batch_size, num_classes), \
        f"Logits shape rách: Kỳ vọng {(batch_size, num_classes)}, Nhận {logits.shape}"
        
    # 3. Kích thước Vector Nén (Latent) phải khớp với d_model thiết kế
    assert latent_vector.shape == (batch_size, d_model), \
        f"Latent vector rách: Kỳ vọng {(batch_size, d_model)}, Nhận {latent_vector.shape}"
        
def test_gradient_flow():
    """Test chức năng Back-prop, nếu đường ống mạng bị cụt thì gradient sẽ bằng None"""
    batch_size = 2
    seq_len = 60
    input_dim = 15
    
    x = torch.randn(batch_size, seq_len, input_dim)
    model = AAMT_Model(input_dim=input_dim, seq_len=seq_len)
    
    reconstructed, logits, _ = model(x)
    
    # Tạo random loss
    loss_recon = torch.nn.functional.mse_loss(reconstructed, x)
    loss_class = torch.nn.functional.cross_entropy(logits, torch.tensor([0, 1]))
    
    total_loss = loss_recon + loss_class
    total_loss.backward()
    
    # Kiểm tra xem trọng số trong Reconstructor có được cập nhật gradient không
    for param in model.reconstructor.parameters():
        assert param.grad is not None, "Dòng chảy Gradient tới Reconstructor Head bị ĐỨT!"
        
    # Kiểm tra xem trọng số trong Classifier có được cập nhật gradient không
    for param in model.classifier.parameters():
        assert param.grad is not None, "Dòng chảy Gradient tới Classification Head bị ĐỨT!"

    # Kiểm tra lưới Transformer Encoder gánh lõi tổng
    for param in model.encoder.parameters():
        assert param.grad is not None, "Dòng chảy Gradient tới ENCODER lõi bị ĐỨT!"
