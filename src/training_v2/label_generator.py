"""
label_generator.py — Soft Label Generator (V2)
================================================
Thay thế nhãn nhị phân cứng (0/1) bằng Soft Labels liên tục [0,1]
tỷ lệ thuận với độ lớn (magnitude) của Log Return T+5.

Công thức:
    log_return = log(P_{t+5} / P_t)
    y_soft     = sigmoid(k · log_return)

Tính chất:
    - Return = 0      → y = 0.50 (trung lập)
    - Return = +2%    → y ≈ 0.95 (tăng mạnh)
    - Return = +0.05% → y ≈ 0.56 (tăng nhẹ)
    - Return = -2%    → y ≈ 0.05 (giảm mạnh)

Lợi ích toán học:
    Gradient Descent nhận được tín hiệu có độ lớn tỷ lệ với biến động thực,
    tránh trường hợp nến +0.001% và +2% cùng gửi gradient bằng nhau.
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class SoftLabelGenerator:
    """
    Tạo Soft Labels cho bài toán phân loại hướng giá T+5.

    Parameters
    ----------
    k : float
        Scale factor cho hàm sigmoid. k lớn → phân biệt mạnh mẽ hơn.
        k=50 tương ứng: return ±2% → y ≈ 0.95/0.05
    min_move_pct : float
        Ngưỡng biến động tối thiểu (absolute log return) để coi là xu hướng.
        Các nến có |log_return| < min_move_pct bị loại khỏi dataset (Sideways filter).
        Mặc định 0.0002 (~0.02%).
    forecast_horizon : int
        Số phút nhìn trước T+N. Mặc định 5.
    """

    def __init__(
        self,
        k: float = 50.0,
        min_move_pct: float = 0.0002,
        forecast_horizon: int = 5,
    ):
        if k <= 0:
            raise ValueError(f"k phải dương, nhận được: {k}")
        if min_move_pct < 0:
            raise ValueError(f"min_move_pct phải >= 0, nhận được: {min_move_pct}")
        if forecast_horizon < 1:
            raise ValueError(f"forecast_horizon phải >= 1, nhận được: {forecast_horizon}")

        self.k = k
        self.min_move_pct = min_move_pct
        self.forecast_horizon = forecast_horizon

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        """Hàm sigmoid an toàn, tránh overflow."""
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

    def compute_log_returns(self, close_series: pd.Series) -> pd.Series:
        """
        Tính log return sau forecast_horizon phút.

        Parameters
        ----------
        close_series : pd.Series
            Chuỗi giá đóng cửa (Close), index là DatetimeIndex.

        Returns
        -------
        pd.Series
            Series log_return[t] = log(P_{t+H} / P_t), aligned với close_series.index.
            Các phần tử ở cuối (< forecast_horizon dòng) sẽ là NaN.
        """
        future_close = close_series.shift(-self.forecast_horizon)
        # Tránh log(0) và log(âm)
        safe_current = close_series.replace(0, np.nan)
        log_return = np.log(future_close / safe_current)
        return log_return

    def generate(
        self, close_series: pd.Series
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Tạo Soft Labels từ chuỗi giá đóng cửa.

        Parameters
        ----------
        close_series : pd.Series
            Chuỗi giá đóng cửa theo thời gian (index là DatetimeIndex).

        Returns
        -------
        soft_labels : pd.Series (dtype float32)
            Nhãn mềm nằm trong (0, 1).
            - > 0.5 : kỳ vọng giá tăng
            - < 0.5 : kỳ vọng giá giảm
        log_returns : pd.Series (dtype float32)
            Log return thực tế (dùng cho EV evaluation).

        Ghi chú
        -------
        Các mẫu Sideways (|log_return| < min_move_pct) bị LOẠI KHỎI index trả về.
        """
        log_returns = self.compute_log_returns(close_series)

        # Loại bỏ NaN cuối (do shift) và NaN đầu (nếu có)
        valid_mask = log_returns.notna()

        # Sideways filter: loại bỏ nến đi ngang
        sideways_mask = log_returns.abs() < self.min_move_pct
        keep_mask = valid_mask & ~sideways_mask

        log_returns_clean = log_returns[keep_mask].astype(np.float32)

        # Tính soft label: y = sigmoid(k * log_return)
        soft_labels = pd.Series(
            self._sigmoid(self.k * log_returns_clean.values),
            index=log_returns_clean.index,
            dtype=np.float32,
            name="soft_label",
        )

        n_sideways = sideways_mask.sum()
        n_total = valid_mask.sum()
        print(
            f"[SoftLabel] Tổng: {n_total:,} | Sideways bị loại: {n_sideways:,} "
            f"({n_sideways/max(n_total,1)*100:.1f}%) | Còn lại: {len(soft_labels):,}"
        )

        buy_ratio = (soft_labels > 0.5).mean()
        print(
            f"[SoftLabel] Phân phối sau filter — BUY (>0.5): {buy_ratio*100:.1f}% | "
            f"SELL (<0.5): {(1-buy_ratio)*100:.1f}%"
        )

        return soft_labels, log_returns_clean

    def to_hard_label(self, soft_labels: pd.Series) -> pd.Series:
        """
        Chuyển soft labels về hard labels (0/1) để tính Win Rate.
        Dùng trong evaluation, không dùng trong training.
        """
        return (soft_labels >= 0.5).astype(np.int64)
