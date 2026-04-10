"""Unit tests cho evaluation module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import pytest
import torch


class TestFindMaxThreshold:
    def test_perfect_confidence_returns_high_threshold(self):
        from core.training.evaluation import find_max_threshold
        # 100 xác suất đều > 0.9 → threshold 0.90 đủ tín hiệu
        probs = torch.full((100,), 0.95)
        t = find_max_threshold(probs, min_signals=10)
        assert t >= 0.90

    def test_all_around_50pct_returns_base(self):
        from core.training.evaluation import find_max_threshold
        # Xác suất đều ~0.5 → không đủ tín hiệu ở bất kỳ threshold nào
        probs = torch.full((100,), 0.51)
        t = find_max_threshold(probs, min_signals=10)
        assert t == 0.50

    def test_min_signals_respected(self):
        from core.training.evaluation import find_max_threshold
        # Chỉ có 5 tín hiệu ở t=0.90, cần 10
        probs = torch.cat([torch.full((5,), 0.95), torch.full((95,), 0.51)])
        t = find_max_threshold(probs, min_signals=10)
        # Phải tìm threshold thấp hơn để có đủ 10 tín hiệu
        assert t < 0.90


class TestBuildThresholds:
    def test_returns_n_steps(self):
        from core.training.evaluation import build_thresholds
        thrs = build_thresholds(0.70, n_steps=4)
        assert len(thrs) == 4

    def test_first_is_050(self):
        from core.training.evaluation import build_thresholds
        thrs = build_thresholds(0.70, n_steps=4)
        assert thrs[0] == pytest.approx(0.50)

    def test_last_is_max_thresh(self):
        from core.training.evaluation import build_thresholds
        thrs = build_thresholds(0.70, n_steps=4)
        assert thrs[-1] == pytest.approx(0.70)

    def test_max_thresh_050_returns_all_050(self):
        from core.training.evaluation import build_thresholds
        thrs = build_thresholds(0.50, n_steps=4)
        assert all(t == pytest.approx(0.50) for t in thrs)


class TestComputeWinrates:
    def test_perfect_prediction(self):
        from core.training.evaluation import compute_winrates
        # BUY: prob=0.95, label=1 → 100% WR
        probs  = torch.tensor([0.95, 0.95, 0.05, 0.05])
        labels = torch.tensor([1,    1,    0,    0   ])
        wrs, totals = compute_winrates(probs, labels, [0.60])
        assert wrs[0] == pytest.approx(1.0)
        assert totals[0] == 4

    def test_zero_signals_returns_zero_wr(self):
        from core.training.evaluation import compute_winrates
        # Tất cả xác suất ở vùng 0.4-0.6, không vượt threshold 0.90
        probs  = torch.full((50,), 0.50)
        labels = torch.zeros(50, dtype=torch.long)
        wrs, totals = compute_winrates(probs, labels, [0.90])
        assert totals[0] == 0
        assert wrs[0] == pytest.approx(0.0)


class TestCalcStrategyScores:
    def test_higher_wr_gives_higher_score(self):
        from core.training.evaluation import calc_strategy_scores
        s1 = calc_strategy_scores([0.5, 0.55, 0.60, 0.65], 0.69)
        s2 = calc_strategy_scores([0.5, 0.55, 0.70, 0.75], 0.69)
        assert s2["L3_1.4_L4_1.0"] > s1["L3_1.4_L4_1.0"]

    def test_lower_val_loss_gives_higher_best_vloss_score(self):
        from core.training.evaluation import calc_strategy_scores
        s1 = calc_strategy_scores([0.5, 0.5, 0.5, 0.5], 0.70)
        s2 = calc_strategy_scores([0.5, 0.5, 0.5, 0.5], 0.60)
        assert s2["BEST_VLOSS"] > s1["BEST_VLOSS"]
