import torch
import torch.nn as nn
import torch.nn.functional as F


class AAMT_JointLoss(nn.Module):
    """
    Hàm mất mát tổng hợp V3.1 (Joint Loss + MSE Gatekeeper).

    Nâng cấp Giải pháp A - Autoencoder làm Kẻ Gác Đền:
    - Tính per-sample MSE reconstruction error.
    - Nếu một sample có MSE vượt ngưỡng (điểm phân vị mse_gate_percentile),
      trọng số CE Loss của sample đó bị nhân về 0.
    - Chỉ những mẫu "quen thuộc" (MSE thấp, AI đã thấy mẫu hình tương tự)
      mới được phép cập nhật trọng số Classification Head.

    Args:
        lambda_recon (float): Trọng số nhánh Reconstruction.
        lambda_class (float): Trọng số nhánh Classification.
        mse_gate_percentile (float): Phân vị MSE để làm ngưỡng lọc (0.0=tắt, 0.75=lọc 25% nhiễu nhất).
    """
    def __init__(self, lambda_recon=1.0, lambda_class=1.0, mse_gate_percentile=0.0):
        super().__init__()
        self.mse_loss = nn.MSELoss()
        # label_smoothing=0.15: ngăn model đặt probability ~0 vào class đúng
        self.ce_loss_mean = nn.CrossEntropyLoss(label_smoothing=0.15, reduction='mean')
        self.ce_loss_none = nn.CrossEntropyLoss(label_smoothing=0.15, reduction='none')

        self.lambda_recon = lambda_recon
        self.lambda_class = lambda_class
        # 0.0 = tắt MSE Gate (hành vi y hệt V3 gốc)
        # 0.75 = lọc bỏ 25% mẫu có MSE cao nhất (nhiễu nhất)
        self.mse_gate_percentile = mse_gate_percentile

    def set_lambdas(self, lambda_recon, lambda_class):
        """Dùng hàm này để rẽ nhánh Train 2 giai đoạn (Warm-up / Fine-tuning)"""
        self.lambda_recon = lambda_recon
        self.lambda_class = lambda_class

    def set_mse_gate(self, percentile: float):
        """Điều chỉnh ngưỡng MSE Gate động (Ví dụ: tăng dần theo epoch)"""
        self.mse_gate_percentile = percentile

    def forward(self, reconstructed, inputs, logits, targets):
        """
        Args:
            reconstructed: [Batch, Seq_len, Features]
            inputs:        [Batch, Seq_len, Features]
            logits:        [Batch, Num_Classes]
            targets:       [Batch] (0=Sell, 1=Buy, 2=Sideway)
        Returns:
            total_loss, loss_recon, loss_class
        """
        targets = targets.long()

        # === Nhánh 1: Reconstruction Loss (toàn bộ Batch) ===
        loss_recon = self.mse_loss(reconstructed, inputs)

        # === Nhánh 2: Classification Loss với MSE Gatekeeper ===
        if self.mse_gate_percentile > 0.0 and self.lambda_class > 0.0:
            # Tính per-sample MSE: [Batch, Seq_len, Features] -> [Batch]
            per_sample_mse = (reconstructed - inputs).pow(2).mean(dim=[1, 2])

            # Tính ngưỡng MSE từ phân phối batch hiện tại
            mse_threshold = torch.quantile(per_sample_mse, self.mse_gate_percentile)

            # Mask = 1 nếu MSE thấp (mẫu quen thuộc), = 0 nếu MSE cao (mẫu nhiễu/lạ)
            gate_mask = (per_sample_mse <= mse_threshold).float()

            n_active = gate_mask.sum().item()
            n_total = gate_mask.shape[0]

            if n_active > 0:
                # Tính CE Loss per-sample rồi nhân mask, bảo toàn gradient
                per_sample_ce = self.ce_loss_none(logits, targets)
                loss_class = (per_sample_ce * gate_mask).sum() / (gate_mask.sum() + 1e-8)
            else:
                # Edge case: tất cả đều nhiễu → dùng mean bình thường
                loss_class = self.ce_loss_mean(logits, targets)
        else:
            # MSE Gate tắt (mse_gate_percentile=0.0): hành vi gốc V3
            loss_class = self.ce_loss_mean(logits, targets)

        # === Tổng hợp ===
        total_loss = (self.lambda_recon * loss_recon) + (self.lambda_class * loss_class)
        return total_loss, loss_recon, loss_class
