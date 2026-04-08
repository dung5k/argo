"""
focal_loss.py — Focal Loss V2 với Soft Label Support
======================================================
Focal Loss: FL(p_t) = -α_t · (1 - p_t)^γ · log(p_t)

Cải tiến so với CrossEntropyLoss thuần:
    - Giảm trọng số gradient cho các mẫu dễ (mô hình đã đoán chắc chắn đúng).
    - Tập trung toàn bộ gradient vào các mẫu khó (vùng đảo chiều phức tạp).
    - Hỗ trợ soft labels [0,1] thay vì chỉ nhãn nguyên (0/1).

Chi tiết toán học:
    p_t   = P(class = y_hard) = softmax logit tương ứng với nhãn thực (hard)
    α_t   = class weight (tự động từ class balance)
    γ     = focusing parameter (mặc định 2.0)
    FL    = -α_t · (1-p_t)^γ · CE_loss

    Với soft labels (y ∈ [0,1]):
        CE được tính bằng Binary Cross-Entropy trên xác suất tăng:
        CE_soft = -(y · log(p_up) + (1-y) · log(1-p_up))
        Sau đó pt = exp(-CE_soft) để tính focal weight.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLossV2(nn.Module):
    """
    Focal Loss hỗ trợ cả hard labels (long) và soft labels (float).

    Parameters
    ----------
    gamma : float
        Focusing parameter. γ=0 → CrossEntropy thuần. γ=2 (khuyến nghị).
    alpha : torch.Tensor | None
        Class weights [weight_class0, weight_class1].
        Nếu None, không áp class weighting.
    use_soft_labels : bool
        True  → input targets là soft labels float ∈ [0,1].
        False → input targets là hard labels long ∈ {0,1}.
    reduction : str
        'mean' hoặc 'sum'.
    """

    def __init__(
        self,
        gamma: float = 2.0,
        alpha: "torch.Tensor | None" = None,
        use_soft_labels: bool = True,
        reduction: str = "mean",
    ):
        super().__init__()
        if gamma < 0:
            raise ValueError(f"gamma phải >= 0, nhận được: {gamma}")

        self.gamma = gamma
        self.alpha = alpha
        self.use_soft_labels = use_soft_labels
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        logits : torch.Tensor, shape (N, 2)
            Raw output của model (chưa qua softmax).
        targets : torch.Tensor
            - Nếu use_soft_labels=True: shape (N,), dtype float, ∈ [0,1].
            - Nếu use_soft_labels=False: shape (N,), dtype long, ∈ {0,1}.

        Returns
        -------
        torch.Tensor
            Scalar loss value.
        """
        if self.use_soft_labels:
            return self._soft_label_focal(logits, targets)
        else:
            return self._hard_label_focal(logits, targets)

    def _soft_label_focal(
        self, logits: torch.Tensor, soft_targets: torch.Tensor
    ) -> torch.Tensor:
        """
        Focal Loss với soft labels.
        Dùng Binary Cross-Entropy trên P(up) để tính cross-entropy base.
        """
        # P(up) = softmax logit thứ 1
        probs = F.softmax(logits, dim=1)       # (N, 2)
        p_up = probs[:, 1].clamp(1e-7, 1 - 1e-7)   # (N,)

        soft = soft_targets.clamp(0.0, 1.0)

        # Binary CE: -(y * log(p) + (1-y) * log(1-p))
        ce_per_sample = -(soft * torch.log(p_up) + (1.0 - soft) * torch.log(1.0 - p_up))

        # Focal weight: pt = exp(-ce) (xác suất "tự tin đúng" tương đương)
        pt = torch.exp(-ce_per_sample)
        focal_weight = (1.0 - pt) ** self.gamma

        # Class weight alpha (theo chiều của soft label)
        if self.alpha is not None:
            alpha_t = self.alpha[1] * soft + self.alpha[0] * (1.0 - soft)
            focal_weight = alpha_t * focal_weight

        loss_per_sample = focal_weight * ce_per_sample

        return loss_per_sample.mean() if self.reduction == "mean" else loss_per_sample.sum()

    def _hard_label_focal(
        self, logits: torch.Tensor, hard_targets: torch.Tensor
    ) -> torch.Tensor:
        """Focal Loss với hard labels (int). Dùng CrossEntropy làm base."""
        ce_per_sample = F.cross_entropy(logits, hard_targets, reduction="none")
        pt = torch.exp(-ce_per_sample)
        focal_weight = (1.0 - pt) ** self.gamma

        if self.alpha is not None:
            alpha_t = self.alpha[hard_targets]
            focal_weight = alpha_t * focal_weight

        loss_per_sample = focal_weight * ce_per_sample

        return loss_per_sample.mean() if self.reduction == "mean" else loss_per_sample.sum()


def build_focal_loss(
    n_buy: int,
    n_sell: int,
    gamma: float = 2.0,
    use_soft_labels: bool = True,
    device: "torch.device | str" = "cpu",
) -> FocalLossV2:
    """
    Factory function: tạo FocalLossV2 với alpha tự động từ class balance.

    Parameters
    ----------
    n_buy : int
        Số lượng mẫu BUY (label > 0.5) trong tập train.
    n_sell : int
        Số lượng mẫu SELL (label <= 0.5) trong tập train.
    gamma : float
        Focusing parameter (mặc định 2.0).
    use_soft_labels : bool
        True nếu dùng soft labels float.
    device : torch.device | str
        Device để đặt alpha tensor.

    Returns
    -------
    FocalLossV2
    """
    n_total = n_buy + n_sell
    if n_total == 0:
        raise ValueError("n_buy + n_sell = 0, không có dữ liệu.")

    weight_sell = n_total / (2.0 * n_sell) if n_sell > 0 else 1.0
    weight_buy  = n_total / (2.0 * n_buy)  if n_buy  > 0 else 1.0

    alpha = torch.tensor([weight_sell, weight_buy], dtype=torch.float32).to(device)

    print(
        f"[FocalLoss] γ={gamma} | α_sell={weight_sell:.3f}, α_buy={weight_buy:.3f} "
        f"| soft_labels={use_soft_labels}"
    )
    return FocalLossV2(gamma=gamma, alpha=alpha, use_soft_labels=use_soft_labels)
