"""
test_label_generator.py — Unit tests cho SoftLabelGenerator
"""

import sys
import os
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.training_v2.label_generator import SoftLabelGenerator


@pytest.fixture
def generator():
    return SoftLabelGenerator(k=50.0, min_move_pct=0.0002, forecast_horizon=5)


@pytest.fixture
def close_series():
    """Chuỗi giá đóng cửa giả lập 200 phút."""
    idx = pd.date_range("2025-01-01", periods=200, freq="1min", tz="UTC")
    np.random.seed(42)
    prices = 2000.0 + np.cumsum(np.random.randn(200) * 0.5)
    return pd.Series(prices, index=idx, name="close")


class TestSigmoidBehavior:
    """Kiểm tra tính chất toán học của hàm sigmoid."""

    def test_return_zero_gives_label_half(self, generator):
        """Return = 0 phải cho label = 0.5 (trung lập)."""
        result = generator._sigmoid(np.array([0.0]))
        assert abs(result[0] - 0.5) < 1e-6

    def test_large_positive_return_gives_label_near_one(self, generator):
        """Return rất lớn (+10%) → label gần 1."""
        log_ret = np.log(1.10)  # +10%
        result = generator._sigmoid(np.array([generator.k * log_ret]))
        assert result[0] > 0.90, f"Expected > 0.90, got {result[0]}"

    def test_large_negative_return_gives_label_near_zero(self, generator):
        """Return âm lớn (-10%) → label gần 0."""
        log_ret = np.log(0.90)  # -10%
        result = generator._sigmoid(np.array([generator.k * log_ret]))
        assert result[0] < 0.10, f"Expected < 0.10, got {result[0]}"

    def test_small_positive_return_gives_label_slightly_above_half(self, generator):
        """Return nhỏ (+0.05%) → label nhỉnh hơn 0.5 nhưng không quá 0.7."""
        log_ret = np.log(1.0005)  # +0.05%
        result = generator._sigmoid(np.array([generator.k * log_ret]))
        assert 0.50 < result[0] < 0.70, f"Expected 0.5-0.7, got {result[0]}"

    def test_symmetry(self, generator):
        """sigmoid(x) + sigmoid(-x) = 1 (tính đối xứng)."""
        x = np.array([0.05, 0.1, 0.5, 2.0])
        y_pos = generator._sigmoid(x)
        y_neg = generator._sigmoid(-x)
        np.testing.assert_allclose(y_pos + y_neg, 1.0, atol=1e-6)

    def test_no_overflow(self, generator):
        """Không có NaN hay Inf khi x cực lớn."""
        x = np.array([-1000.0, -500.0, 500.0, 1000.0])
        result = generator._sigmoid(x)
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))


class TestLogReturns:
    """Kiểm tra tính toán log return T+5."""

    def test_shape(self, generator, close_series):
        log_rets = generator.compute_log_returns(close_series)
        assert len(log_rets) == len(close_series)

    def test_last_5_are_nan(self, generator, close_series):
        """5 phần tử cuối phải NaN vì shift(-5) không có dữ liệu."""
        log_rets = generator.compute_log_returns(close_series)
        assert log_rets.iloc[-5:].isna().all()

    def test_first_values_not_nan(self, generator, close_series):
        """Các giá trị đầu (trừ 5 cuối) không được NaN."""
        log_rets = generator.compute_log_returns(close_series)
        assert log_rets.iloc[:-5].notna().all()


class TestSidewaysFilter:
    """Kiểm tra bộ lọc Sideways."""

    def test_sideways_candles_are_removed(self, generator):
        """Các nến có |return| < min_move_pct phải bị loại."""
        idx = pd.date_range("2025-01-01", periods=20, freq="1min", tz="UTC")
        # Tạo chuỗi giá không đổi (return = 0 → sideways)
        prices = pd.Series([2000.0] * 20, index=idx)
        soft, rets = generator.generate(prices)
        # Tất cả sideways + 5 NaN cuối → phải rỗng
        assert len(soft) == 0

    def test_trending_candles_are_kept(self, generator):
        """Nến có xu hướng rõ ràng phải được giữ lại."""
        idx = pd.date_range("2025-01-01", periods=20, freq="1min", tz="UTC")
        # Tạo trend mạnh: +1% mỗi nến
        prices = pd.Series([2000.0 * (1.01 ** i) for i in range(20)], index=idx)
        soft, rets = generator.generate(prices)
        assert len(soft) > 0

    def test_output_range(self, generator, close_series):
        """Tất cả soft labels phải nằm trong (0,1)."""
        soft, rets = generator.generate(close_series)
        if len(soft) > 0:
            assert soft.min() > 0.0
            assert soft.max() < 1.0


class TestHardLabel:
    """Kiểm tra convert soft → hard labels."""

    def test_above_half_is_one(self, generator):
        soft = pd.Series([0.6, 0.8, 0.4, 0.2])
        hard = generator.to_hard_label(soft)
        expected = pd.Series([1, 1, 0, 0])
        pd.testing.assert_series_equal(hard, expected, check_dtype=False)

    def test_exactly_half_is_one(self, generator):
        """Nhãn = 0.5 được coi là BUY (>= 0.5)."""
        soft = pd.Series([0.5])
        hard = generator.to_hard_label(soft)
        assert hard.iloc[0] == 1


class TestInvalidInputs:
    """Kiểm tra validation đầu vào."""

    def test_negative_k_raises(self):
        with pytest.raises(ValueError, match="k phải dương"):
            SoftLabelGenerator(k=-1.0)

    def test_negative_min_move_raises(self):
        with pytest.raises(ValueError, match="min_move_pct"):
            SoftLabelGenerator(min_move_pct=-0.1)

    def test_zero_horizon_raises(self):
        with pytest.raises(ValueError, match="forecast_horizon"):
            SoftLabelGenerator(forecast_horizon=0)
