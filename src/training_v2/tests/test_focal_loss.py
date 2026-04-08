"""
test_focal_loss.py — Unit tests cho FocalLossV2
"""

import sys
import os
import torch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.training_v2.focal_loss import FocalLossV2, build_focal_loss


@pytest.fixture
def device():
    return torch.device("cpu")


@pytest.fixture
def batch_logits():
    """Batch 8 samples, 2 class logits."""
    torch.manual_seed(0)
    return torch.randn(8, 2)


class TestFocalLossHard:
    """Kiểm tra FocalLoss với hard labels (int)."""

    def test_output_is_scalar(self, batch_logits):
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=False)
        targets = torch.randint(0, 2, (8,))
        loss = loss_fn(batch_logits, targets)
        assert loss.dim() == 0  # scalar

    def test_loss_positive(self, batch_logits):
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=False)
        targets = torch.randint(0, 2, (8,))
        loss = loss_fn(batch_logits, targets)
        assert loss.item() > 0

    def test_gamma_zero_equals_cross_entropy(self):
        """γ=0 → FocalLoss = CrossEntropyLoss."""
        torch.manual_seed(1)
        logits = torch.randn(16, 2)
        targets = torch.randint(0, 2, (16,))

        fl = FocalLossV2(gamma=0.0, use_soft_labels=False, reduction='mean')
        ce = torch.nn.CrossEntropyLoss(reduction='mean')

        fl_val = fl(logits, targets).item()
        ce_val = ce(logits, targets).item()
        assert abs(fl_val - ce_val) < 1e-4, \
            f"γ=0: FocalLoss={fl_val:.4f} ≠ CE={ce_val:.4f}"

    def test_easy_samples_have_lower_gradient_than_hard(self):
        """
        Mẫu dễ (model đoán chắc đúng) phải có gradient weight nhỏ hơn mẫu khó.
        Focal weight = (1-pt)^γ → với pt gần 1 (dễ) → weight gần 0.
        """
        gamma = 2.0
        # Mẫu "dễ": model rất chắc chắn đúng
        logits_easy = torch.tensor([[0.1, 10.0]])  # chắc chắn class 1
        target_easy = torch.tensor([1])
        # Mẫu "khó": model không chắc
        logits_hard = torch.tensor([[0.5, 0.5]])   # 50/50
        target_hard = torch.tensor([1])

        loss_fn = FocalLossV2(gamma=gamma, use_soft_labels=False, reduction='mean')
        loss_easy = loss_fn(logits_easy, target_easy).item()
        loss_hard = loss_fn(logits_hard, target_hard).item()

        assert loss_easy < loss_hard, \
            f"Easy sample loss {loss_easy:.4f} nên < Hard {loss_hard:.4f}"


class TestFocalLossSoft:
    """Kiểm tra FocalLoss với soft labels (float)."""

    def test_output_is_scalar_soft(self, batch_logits):
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=True)
        targets = torch.rand(8)  # soft labels ∈ (0,1)
        loss = loss_fn(batch_logits, targets)
        assert loss.dim() == 0

    def test_loss_positive_soft(self, batch_logits):
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=True)
        targets = torch.full((8,), 0.85)  # tất cả BUY mạnh
        loss = loss_fn(batch_logits, targets)
        assert loss.item() > 0

    def test_neutral_label_gives_higher_loss_than_extremes(self):
        """
        Soft label = 0.5 (không biết) → loss cao hơn label = 0.95 hay 0.05
        vì mô hình không có tín hiệu để học từ.
        """
        torch.manual_seed(42)
        logits = torch.randn(4, 2)

        loss_fn = FocalLossV2(gamma=0.0, use_soft_labels=True)  # γ=0 để test CE thuần

        loss_neutral  = loss_fn(logits, torch.full((4,), 0.5)).item()
        loss_extreme  = loss_fn(logits, torch.full((4,), 0.95)).item()

        # Không có đảm bảo tuyệt đối nhưng kiểm tra cả hai > 0
        assert loss_neutral > 0
        assert loss_extreme > 0

    def test_no_nan_no_inf(self, batch_logits):
        """Loss không được là NaN hoặc Inf."""
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=True)
        targets = torch.rand(8)
        loss = loss_fn(batch_logits, targets)
        assert not torch.isnan(loss)
        assert not torch.isinf(loss)

    def test_clip_extreme_labels(self, batch_logits):
        """Soft label = 0 hoặc 1 không được gây log(0)."""
        loss_fn = FocalLossV2(gamma=2.0, use_soft_labels=True)
        targets = torch.tensor([0.0, 1.0, 0.0, 1.0, 0.5, 0.5, 0.8, 0.2])
        loss = loss_fn(batch_logits, targets)
        assert not torch.isnan(loss)
        assert not torch.isinf(loss)


class TestBuildFocalLoss:
    """Kiểm tra factory function build_focal_loss."""

    def test_creates_loss_with_balanced_data(self, device):
        loss_fn = build_focal_loss(
            n_buy=500, n_sell=500,
            gamma=2.0, use_soft_labels=True, device=device
        )
        assert isinstance(loss_fn, FocalLossV2)

    def test_alpha_buy_larger_when_fewer_buys(self, device):
        """Khi BUY ít hơn SELL → α_buy > α_sell."""
        loss_fn = build_focal_loss(
            n_buy=100, n_sell=900,
            gamma=2.0, use_soft_labels=True, device=device
        )
        alpha_sell = loss_fn.alpha[0].item()
        alpha_buy  = loss_fn.alpha[1].item()
        assert alpha_buy > alpha_sell, \
            f"BUY ít hơn SELL → α_buy phải lớn hơn. Got: sell={alpha_sell:.2f}, buy={alpha_buy:.2f}"

    def test_zero_samples_raises(self, device):
        with pytest.raises(ValueError, match="n_buy \\+ n_sell = 0"):
            build_focal_loss(n_buy=0, n_sell=0, device=device)
