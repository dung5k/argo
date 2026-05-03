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
    def __init__(self, lambda_recon=1.0, lambda_class=1.0, mse_gate_percentile=0.0, class_weights=None, focal_gamma=2.0, label_smoothing=0.15):
        super().__init__()
        self.mse_loss = nn.MSELoss()
        
        # Áp dụng class_weights để chống Bias Sideway
        if class_weights is not None:
            # Đảm bảo class_weights là tensor
            if not isinstance(class_weights, torch.Tensor):
                class_weights = torch.tensor(class_weights, dtype=torch.float32)
        
        # label_smoothing: ngăn model đặt probability ~0 vào class đúng
        self.ce_loss_mean = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing, reduction='mean')
        self.ce_loss_none = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=label_smoothing, reduction='none')

        self.lambda_recon = lambda_recon
        self.lambda_class = lambda_class
        # 0.0 = tắt MSE Gate (hành vi y hệt V3 gốc)
        # 0.75 = lọc bỏ 25% mẫu có MSE cao nhất (nhiễu nhất)
        self.mse_gate_percentile = mse_gate_percentile
        
        # Focal Loss gamma parameter (0.0 = tắt Focal Loss)
        self.focal_gamma = focal_gamma

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

        # === Nhánh 2: Classification Loss với Focal Loss & MSE Gatekeeper ===
        if self.lambda_class > 0.0:
            # Tính CE cơ bản (đã bao gồm class_weights và label_smoothing)
            per_sample_ce = self.ce_loss_none(logits, targets)
            
            # Áp dụng Focal Loss (ép mạng học các case bị dính Stoploss/Judas Swing)
            if self.focal_gamma > 0.0:
                probs = F.softmax(logits, dim=1)
                # Lấy xác suất pt của class đúng
                pt = probs.gather(1, targets.unsqueeze(1)).squeeze(1)
                focal_weight = (1.0 - pt) ** self.focal_gamma
                per_sample_loss = per_sample_ce * focal_weight
            else:
                per_sample_loss = per_sample_ce

            # MSE Gatekeeper: Lọc nhiễu
            if self.mse_gate_percentile > 0.0:
                # Tính per-sample MSE: [Batch, Seq_len, Features] -> [Batch]
                per_sample_mse = (reconstructed - inputs).pow(2).mean(dim=[1, 2])
                
                # Tính ngưỡng MSE từ phân phối batch hiện tại
                mse_threshold = torch.quantile(per_sample_mse, self.mse_gate_percentile)
                
                # Mask = 1 nếu MSE thấp (mẫu quen thuộc), = 0 nếu MSE cao (mẫu nhiễu/lạ)
                gate_mask = (per_sample_mse <= mse_threshold).float()
                
                n_active = gate_mask.sum().item()
                if n_active > 0:
                    loss_class = (per_sample_loss * gate_mask).sum() / (gate_mask.sum() + 1e-8)
                else:
                    loss_class = per_sample_loss.mean()
            else:
                loss_class = per_sample_loss.mean()
        else:
            loss_class = torch.tensor(0.0, device=logits.device)

        # === Tổng hợp ===
        total_loss = (self.lambda_recon * loss_recon) + (self.lambda_class * loss_class)
        return total_loss, loss_recon, loss_class
