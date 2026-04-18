import torch
import torch.nn as nn
import torch.nn.functional as F

class AAMT_JointLoss(nn.Module):
    """
    Hàm mất mát tổng hợp của V3.0 (Joint Loss).
    Tối ưu đồng thời 2 nhánh:
    1. Reconstruction Loss (MSE): Đánh giá lỗi khi khôi phục lại input tensor.
    2. Classification Loss (Cross Entropy): Đánh giá lỗi khi phân loại (Buy/Sell/Sideway).

    Args:
        class_weights: Tensor [num_classes] — trọng số nghịch đảo tần suất nhãn.
            Nên tính bằng: total / (num_classes * class_count) để bù đắp mất cân bằng
            tự nhiên của thị trường (VD: 1 Buy : 5 Sell do Downtrend kéo dài).
    """
    def __init__(self, lambda_recon=1.0, lambda_class=1.0, class_weights: torch.Tensor = None):
        super().__init__()
        self.mse_loss = nn.MSELoss()

        # Nếu được truyền class_weights, CrossEntropy sẽ phạt nặng hơn khi đoán sai lớp thiểu số
        if class_weights is not None:
            self.ce_loss = nn.CrossEntropyLoss(weight=class_weights)
        else:
            self.ce_loss = nn.CrossEntropyLoss()

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
            targets: Tensor [Batch] (nhãn gán: 0=Sell, 1=Buy, 2=Sideway)
        """
        # Nhánh 1: Autoencoder Loss
        loss_recon = self.mse_loss(reconstructed, inputs)

        # Nhánh 2: Classification Loss (có trọng số nếu được cung cấp)
        targets = targets.long()
        loss_class = self.ce_loss(logits, targets)

        # Hàm tổng
        total_loss = (self.lambda_recon * loss_recon) + (self.lambda_class * loss_class)

        return total_loss, loss_recon, loss_class

