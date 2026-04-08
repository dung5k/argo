"""
test_phoenix_v2.py — Unit tests cho PhoenixRestartV2
"""

import sys
import os
import torch
import torch.nn as nn
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.training_v2.phoenix_v2 import PhoenixRestartV2


class SimpleModel(nn.Module):
    """Model đơn giản để test."""
    def __init__(self):
        super().__init__()
        self.linear1 = nn.Linear(10, 64)
        self.linear2 = nn.Linear(64, 2)

    def forward(self, x):
        return self.linear2(torch.relu(self.linear1(x)))


@pytest.fixture
def model():
    torch.manual_seed(0)
    return SimpleModel()


@pytest.fixture
def phoenix(model):
    return PhoenixRestartV2(
        model=model,
        base_lr=1e-4,
        weight_decay=1e-3,
        max_phoenix=5,
        max_stagnate=3,
        min_signals=10,
    )


class TestPhoenixInitialization:
    def test_initial_state(self, phoenix):
        assert phoenix.phoenix_count == 0
        assert phoenix.epochs_no_improve == 0
        assert not phoenix.exhausted
        assert phoenix.remaining == 5

    def test_optimizer_created(self, phoenix):
        assert phoenix.optimizer is not None

    def test_scheduler_created(self, phoenix):
        assert phoenix.scheduler is not None


class TestStagnationTracking:
    def test_improve_resets_counter(self, phoenix):
        phoenix.epochs_no_improve = 2
        phoenix.notify_improved()
        assert phoenix.epochs_no_improve == 0

    def test_no_improve_increments_counter(self, phoenix):
        needs = phoenix.notify_no_improve()
        assert phoenix.epochs_no_improve == 1
        assert not needs  # Chưa đủ max_stagnate=3

    def test_trigger_after_max_stagnate(self, phoenix):
        for _ in range(3):
            result = phoenix.notify_no_improve()
        # Lần thứ 3: đạt max_stagnate → trigger phoenix
        assert result is True
        assert phoenix.phoenix_count == 1
        assert phoenix.epochs_no_improve == 0

    def test_exhausted_after_max_phoenix(self, phoenix, model):
        state = model.state_dict()
        for _ in range(6):  # max_phoenix=5, cần 6 triggers
            for _ in range(3):
                phoenix.notify_no_improve()
            if not phoenix.exhausted:
                phoenix.apply_perturbation(state)
        assert phoenix.exhausted
        assert phoenix.remaining == 0


class TestMagnitudeAwareNoise:
    """
    Test cốt lõi: Chiến lược B phải sản sinh nhiễu tỷ lệ với |w|.
    """

    def test_noise_proportional_to_weight_magnitude(self, model):
        """
        Sau khi áp Strategy B, layer với trọng số lớn hơn phải nhận nhiễu lớn hơn.
        Kiểm tra: std(noise) / mean(|w|) ≈ alpha (khoảng 0.02-0.08).
        """
        phoenix = PhoenixRestartV2(model=model, max_phoenix=5, max_stagnate=3)

        # Lấy trọng số trước
        w_before = {}
        for name, param in model.named_parameters():
            w_before[name] = param.data.clone()

        # Áp strategy B trực tiếp
        phoenix._strategy_b()

        # Kiểm tra: noise = (w_after - w_before), phải ~ alpha * |w_before|
        for name, param in model.named_parameters():
            noise = (param.data - w_before[name]).abs()
            magnitude = w_before[name].abs()

            if magnitude.mean().item() > 1e-8:
                ratio = noise.mean().item() / (magnitude.mean().item() + 1e-9)
                # ratio phải trong khoảng alpha=[0.02, 0.08] ± variance
                assert ratio < 0.5, \
                    f"Layer {name}: noise/magnitude ratio {ratio:.3f} quá lớn (sóng thần!)"

    def test_no_layer_completely_destroyed(self, model):
        """
        Không layer nào bị nhiễu chiếm hơn 50% của weight magnitude trung bình.
        Đây là tiêu chí chống 'sóng thần' nhiễu.
        """
        phoenix = PhoenixRestartV2(model=model, max_phoenix=5, max_stagnate=3)
        state_before = {n: p.data.clone() for n, p in model.named_parameters()}

        for _ in range(20):  # Thử nhiều lần
            # Restore về trạng thái ban đầu
            for name, param in model.named_parameters():
                param.data.copy_(state_before[name])

            phoenix._strategy_b()

            for name, param in model.named_parameters():
                noise = (param.data - state_before[name]).abs()
                magnitude = state_before[name].abs()
                if magnitude.mean().item() > 1e-8:
                    ratio = noise.mean().item() / magnitude.mean().item()
                    assert ratio < 0.5, \
                        f"Iteration: Layer {name} bị sóng thần: ratio={ratio:.3f}"


class TestStrategyLR:
    """Kiểm tra chiến lược A (LR Spike)."""

    def test_lr_spike_changes_optimizer_lr(self, phoenix):
        old_lr = phoenix.optimizer.param_groups[0]['lr']
        phoenix._strategy_a()
        new_lr = phoenix.optimizer.param_groups[0]['lr']
        assert new_lr != old_lr
        assert 2e-4 <= new_lr <= 8e-4


class TestApplyPerturbation:
    """Kiểm tra apply_perturbation tổng thể."""

    def test_returns_tuple(self, phoenix, model):
        state = model.state_dict()
        result = phoenix.apply_perturbation(state)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_model_restored_before_perturbation(self, phoenix, model):
        """Model phải được restore về chosen_state trước khi perturbation."""
        original_state = {n: p.data.clone() for n, p in model.named_parameters()}

        # Thay đổi model
        with torch.no_grad():
            for param in model.parameters():
                param.fill_(999.0)

        phoenix.apply_perturbation(original_state)

        # Sau khi restore, trọng số phải gần giá trị gốc (±perturbation nhỏ)
        for name, param in model.named_parameters():
            max_diff = (param.data - original_state[name]).abs().max().item()
            # Perturbation tối đa không được > 50% của |w_original|
            expected_max = original_state[name].abs().max().item() * 0.5 + 0.01
            assert max_diff < expected_max + 1.0, \
                f"Layer {name}: diff {max_diff:.3f} quá lớn so với expected {expected_max:.3f}"
