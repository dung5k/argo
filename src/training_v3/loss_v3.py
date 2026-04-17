import torch
import torch.nn as nn
import torch.nn.functional as F

class AAMT_JointLoss(nn.Module):
    """
    Hàm mất mát tổng hợp của V3.0 (Joint Loss).
    Tối ưu đồng thời 2 nhánh:
    1. Reconstruction Loss (MSE): Đánh giá lỗi khi khôi phục lại input tensor.
    2. Classification Loss (Cross Entropy): Đánh giá lỗi khi phân loại (Buy/Sell/Sideway).
    """
    def __init__(self, lambda_recon=1.0, lambda_class=1.0):
        super().__init__()
        self.mse_loss = nn.MSELoss()
        self.ce_loss = nn.CrossEntropyLoss()
        
        # Các trọng số điều phối sự tập trung của mạng học
        self.lambda_recon = lambda_recon
        self.lambda_class = lambda_class
        
    def set_lambdas(self, lambda_recon, lambda_class):
        """Dùng hàm này để rẽ nhánh Train 2 giai đoạn (Warm-up / Fine-tuning)"""
        self.lambda_recon = lambda_recon
        self.lambda_class = lambda_class
        
    def forward(self, reconstructed, inputs, logits, targets):
        """
        Tính toán tổng Loss
        Args:
            reconstructed: Tensor [Batch, Seq_len, Features] (đầu ra của Reconstruct Head)
            inputs: Tensor [Batch, Seq_len, Features] (dữ liệu nến gốc đầu vào)
            logits: Tensor [Batch, Num_Classes] (kết quả dự báo chưa normalize)
            targets: Tensor [Batch] (nhãn gán: 0, 1, 2)
        """
        # Nhánh 1: Autoencoder Loss
        # Tính toán lỗi hình thái xem vẽ lại biểu đồ nến có chuẩn không
        loss_recon = self.mse_loss(reconstructed, inputs)
        
        # Nhánh 2: Classification Loss
        # Tính toán sai số việc đoán Buy/Sell/Sideway
        # Yêu cầu target phải là giá trị kiểu Long (int64) đối với CrossEntropy
        targets = targets.long()
        loss_class = self.ce_loss(logits, targets)
        
        # Hàm tổng
        total_loss = (self.lambda_recon * loss_recon) + (self.lambda_class * loss_class)
        
        return total_loss, loss_recon, loss_class
