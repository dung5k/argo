"""
test_evaluator_v2.py — Unit tests cho EVEvaluator
"""

import sys
import os
import math
import torch
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.training_v2.evaluator_v2 import EVEvaluator, EpochEvalResult, ThresholdMetrics


@pytest.fixture
def evaluator():
    return EVEvaluator(min_signals=5, n_thresholds=4)


def _make_tensors(n: int, win_rate: float, avg_return: float, seed: int = 0):
    """Tạo probs, hard_labels, log_returns với win rate và return cố định (giả lập)."""
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Tất cả signals vượt threshold 0.6
    probs_up = torch.full((n,), 0.75)       # tất cả là BUY signal (>0.6)
    n_correct = int(n * win_rate)
    labels = torch.zeros(n, dtype=torch.long)
    labels[:n_correct] = 1                  # n_correct đúng

    # Log returns: winner có return dương, loser có return âm
    rets = torch.full((n,), -avg_return)
    rets[:n_correct] = avg_return

    return probs_up, labels, rets


class TestEVCalculation:
    """Kiểm tra tính toán Expected Value."""

    def test_ev_positive_when_wr_high_and_avg_win_large(self, evaluator):
        """WR=70%, avg_win > avg_loss → EV phải dương."""
        n = 100
        probs_up, labels, rets = _make_tensors(n, win_rate=0.7, avg_return=0.002)
        result = evaluator.evaluate(
            probs_up=probs_up,
            hard_labels=labels,
            log_returns=rets,
            val_loss=0.5,
        )
        # Tại threshold 0.5 (L1), kiểm tra EV dương
        l1_metric = result.threshold_metrics[0]
        assert l1_metric.ev_score > 0, \
            f"EV phải dương với WR=70%. Got {l1_metric.ev_score:.4f}"

    def test_ev_negative_when_losses_are_huge(self, evaluator):
        """
        WR=70% nhưng loss magnitude gấp 5× win → EV âm.
        Đây là trường hợp Win Rate cao nhưng expectancy âm.
        """
        n = 100
        probs_up = torch.full((n,), 0.75)
        labels = torch.zeros(n, dtype=torch.long)
        labels[:70] = 1  # 70% đúng

        # Winner: return nhỏ (+0.001), Loser: return lớn (-0.005)
        rets = torch.full((n,), -0.005)
        rets[:70] = 0.001

        result = evaluator.evaluate(
            probs_up=probs_up,
            hard_labels=labels,
            log_returns=rets,
            val_loss=0.5,
        )
        l1 = result.threshold_metrics[0]
        assert l1.ev_score < 0, \
            f"EV phải âm khi loss magnitude >> win. Got EV={l1.ev_score:.4f}"

    def test_ev_zero_for_random_model(self, evaluator):
        """
        Model hoàn toàn random (WR=50%, avg_win=avg_loss) → EV ≈ 0.
        """
        n = 200
        probs_up = torch.full((n,), 0.75)
        hard_labels = torch.zeros(n, dtype=torch.long)
        hard_labels[:100] = 1  # chính xác 50%

        avg_return = 0.002
        rets = torch.tensor(
            [avg_return if i < 100 else -avg_return for i in range(n)],
            dtype=torch.float32
        )

        result = evaluator.evaluate(
            probs_up=probs_up,
            hard_labels=hard_labels,
            log_returns=rets,
            val_loss=0.5,
        )
        l1 = result.threshold_metrics[0]
        # EV = 0.5 * 0.002 - 0.5 * 0.002 = 0
        assert abs(l1.ev_score) < 1e-4, \
            f"Random model EV phải ≈ 0. Got {l1.ev_score:.6f}"


class TestThresholdBehavior:
    """Kiểm tra hành vi các ngưỡng threshold."""

    def test_higher_threshold_fewer_signals(self, evaluator):
        """Ngưỡng cao hơn → ít tín hiệu hơn."""
        n = 100
        probs_up = torch.linspace(0.51, 0.99, n)
        labels = torch.ones(n, dtype=torch.long)
        rets = torch.full((n,), 0.001)

        result = evaluator.evaluate(probs_up, labels, rets, val_loss=0.3)

        # L1 (ngưỡng thấp) phải có nhiều signal hơn L4 (ngưỡng cao)
        n_l1 = result.threshold_metrics[0].total_signals
        n_l4 = result.threshold_metrics[3].total_signals
        assert n_l1 >= n_l4, f"L1 signals ({n_l1}) phải >= L4 signals ({n_l4})"

    def test_n_thresholds_matches_config(self, evaluator):
        """Số ngưỡng phải đúng với cấu hình (4)."""
        n = 100
        probs_up = torch.full((n,), 0.75)
        labels = torch.ones(n, dtype=torch.long)
        rets = torch.full((n,), 0.001)

        result = evaluator.evaluate(probs_up, labels, rets, val_loss=0.3)
        assert len(result.threshold_metrics) == 4


class TestCompositeScore:
    """Kiểm tra tính toán composite score."""

    def test_composite_score_weighted(self):
        """Composite score phải tính đúng trọng số L3 vs L4."""
        m = [
            ThresholdMetrics(0.5, 50, 0.6, 0.002, 0.001, ev_score=0.0006),
            ThresholdMetrics(0.6, 40, 0.65, 0.0025, 0.001, ev_score=0.0009),
            ThresholdMetrics(0.7, 30, 0.70, 0.003, 0.001, ev_score=0.0014),  # L3
            ThresholdMetrics(0.8, 20, 0.75, 0.0035, 0.001, ev_score=0.0019),  # L4
        ]
        result = EpochEvalResult(threshold_metrics=m)
        score = result.composite_score(w_l3=1.4, w_l4=1.0, weight_sum=2.4)
        expected = (1.4 * 0.0014 + 1.0 * 0.0019) / 2.4
        assert abs(score - expected) < 1e-9, f"Got {score}, expected {expected}"

    def test_composite_score_empty_returns_zero(self):
        result = EpochEvalResult(threshold_metrics=[])
        assert result.composite_score() == 0.0


class TestStatisticalValidity:
    """Kiểm tra is_statistically_valid."""

    def test_valid_when_l4_has_enough_signals(self, evaluator):
        n = 100
        probs_up = torch.full((n,), 0.75)
        labels = torch.ones(n, dtype=torch.long)
        rets = torch.full((n,), 0.001)

        result = evaluator.evaluate(probs_up, labels, rets, val_loss=0.3)
        # min_signals=5, L4 chắc chắn có đủ
        assert evaluator.is_statistically_valid(result)

    def test_invalid_when_empty(self, evaluator):
        result = EpochEvalResult(threshold_metrics=[])
        assert not evaluator.is_statistically_valid(result)


class TestSharpeScore:
    """Kiểm tra Sharpe-like score."""

    def test_sharpe_non_nan(self, evaluator):
        """Sharpe score không được NaN."""
        n = 50
        probs_up = torch.full((n,), 0.75)
        labels = torch.ones(n, dtype=torch.long)
        rets = (torch.randn(n) * 0.001 + 0.0005).float()

        result = evaluator.evaluate(probs_up, labels, rets.float(), val_loss=0.3)
        for m in result.threshold_metrics:
            assert not math.isnan(m.sharpe_score), \
                f"Sharpe NaN tại threshold {m.threshold}"
