"""
evaluator_v2.py — Expected Value (EV) Evaluator V2
====================================================
Thay thế tiêu chí đánh giá Win Rate (WR) đơn thuần bằng Expected Value (EV).

Vấn đề toán học của Win Rate:
    WR = 70% không đảm bảo lợi nhuận nếu các lệnh sai xảy ra ở nến biên độ lớn.
    Kỳ vọng thực: E[X] = WR × AvgWin - LR × AvgLoss
    E[X] có thể âm dù WR cao.

Expected Value Score:
    EV = WR × AvgWinReturn - (1 - WR) × AvgLossReturn

    Trong đó:
        WR           = tỷ lệ dự đoán đúng tại ngưỡng threshold
        AvgWinReturn = E[|log_return| | dự đoán đúng] (pip trung bình nếu thắng)
        AvgLossReturn= E[|log_return| | dự đoán sai]  (pip trung bình nếu thua)

Sharpe-like Score (tùy chọn):
    Sharpe = EV / std(log_return) × sqrt(N)
"""

import numpy as np
import torch
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class ThresholdMetrics:
    """Kết quả đánh giá tại một ngưỡng threshold cụ thể."""

    threshold: float
    total_signals: int
    win_rate: float
    avg_win_return: float      # |log_return| trung bình khi đúng
    avg_loss_return: float     # |log_return| trung bình khi sai
    ev_score: float            # Expected Value
    sharpe_score: float = 0.0  # Sharpe-like score (optional)

    def __str__(self) -> str:
        return (
            f">={self.threshold*100:.0f}%: "
            f"WR={self.win_rate*100:.1f}% | "
            f"EV={self.ev_score*10000:.2f}pip | "
            f"N={self.total_signals}"
        )


@dataclass
class EpochEvalResult:
    """Kết quả evaluation của một epoch."""

    threshold_metrics: List[ThresholdMetrics] = field(default_factory=list)
    max_threshold: float = 0.50
    best_ev: float = 0.0
    val_loss: float = float("inf")

    def composite_score(
        self,
        w_l3: float = 1.4,
        w_l4: float = 1.0,
        weight_sum: float = 2.4,
    ) -> float:
        """
        Score tổng hợp L3 + L4 (tương tự calc_strats trong V1 nhưng dùng EV).
        L3 = ngưỡng thứ 3 (index 2), L4 = ngưỡng thứ 4 (index 3).
        """
        if len(self.threshold_metrics) < 4:
            return 0.0
        ev_l3 = self.threshold_metrics[2].ev_score
        ev_l4 = self.threshold_metrics[3].ev_score
        return (w_l3 * ev_l3 + w_l4 * ev_l4) / weight_sum


class EVEvaluator:
    """
    Tính Expected Value score từ validation batch.

    Parameters
    ----------
    min_signals : int
        Số tín hiệu tối thiểu tại ngưỡng cao nhất để kết quả có giá trị thống kê.
    n_thresholds : int
        Số ngưỡng đánh giá (L1..L4). Mặc định 4.
    """

    def __init__(self, min_signals: int = 30, n_thresholds: int = 4):
        self.min_signals = min_signals
        self.n_thresholds = n_thresholds

    def _find_max_threshold(
        self,
        probs_up: torch.Tensor,
    ) -> float:
        """
        Tìm ngưỡng cao nhất mà vẫn có đủ >= min_signals tín hiệu.
        Quét từ 0.99 xuống 0.51.
        """
        max_thresh = 0.50
        for t_int in range(99, 51, -1):
            t = t_int / 100.0
            n_buy  = (probs_up > t).sum().item()
            n_sell = (probs_up < (1.0 - t)).sum().item()
            if (n_buy + n_sell) >= self.min_signals:
                max_thresh = t
                break
        return max_thresh

    def _compute_threshold_metrics(
        self,
        probs_up: torch.Tensor,
        hard_labels: torch.Tensor,
        log_returns: torch.Tensor,
        threshold: float,
    ) -> ThresholdMetrics:
        """
        Tính các chỉ số tại một ngưỡng threshold.

        Parameters
        ----------
        probs_up    : (N,) xác suất model dự báo tăng
        hard_labels : (N,) nhãn thực 0/1
        log_returns : (N,) log return thực tế T+5 (float)
        threshold   : float, ngưỡng xét BUY signal
        """
        lo = 1.0 - threshold

        buy_mask  = probs_up > threshold
        sell_mask = probs_up < lo

        # True Positive: BUY đúng (label=1), True Negative: SELL đúng (label=0)
        correct_buy  = buy_mask  & (hard_labels == 1)
        correct_sell = sell_mask & (hard_labels == 0)
        wrong_buy    = buy_mask  & (hard_labels == 0)
        wrong_sell   = sell_mask & (hard_labels == 1)

        n_signals = buy_mask.sum().item() + sell_mask.sum().item()
        n_correct = correct_buy.sum().item() + correct_sell.sum().item()

        win_rate = n_correct / n_signals if n_signals > 0 else 0.0

        # Tính pip trung bình theo log_return (absolute value)
        abs_ret = log_returns.abs()

        win_mask  = correct_buy | correct_sell
        loss_mask = wrong_buy   | wrong_sell

        avg_win_ret  = abs_ret[win_mask].mean().item()  if win_mask.sum()  > 0 else 0.0
        avg_loss_ret = abs_ret[loss_mask].mean().item() if loss_mask.sum() > 0 else 0.0

        ev = win_rate * avg_win_ret - (1.0 - win_rate) * avg_loss_ret

        # Sharpe-like: EV / std(log_return của signals)
        signal_rets = log_returns[buy_mask | sell_mask]
        std_ret = signal_rets.std().item() if len(signal_rets) > 1 else 1e-9
        sharpe = ev / (std_ret + 1e-9) * (n_signals ** 0.5)

        return ThresholdMetrics(
            threshold=threshold,
            total_signals=n_signals,
            win_rate=win_rate,
            avg_win_return=avg_win_ret,
            avg_loss_return=avg_loss_ret,
            ev_score=ev,
            sharpe_score=sharpe,
        )

    def evaluate(
        self,
        probs_up: torch.Tensor,
        hard_labels: torch.Tensor,
        log_returns: torch.Tensor,
        val_loss: float,
    ) -> EpochEvalResult:
        """
        Đánh giá toàn bộ một epoch.

        Parameters
        ----------
        probs_up    : (N,) xác suất model dự đoán giá tăng (sau softmax).
        hard_labels : (N,) nhãn thực (long) 0 = SELL, 1 = BUY.
        log_returns : (N,) log return thực tế T+5.
        val_loss    : float, giá trị validation loss trung bình epoch này.

        Returns
        -------
        EpochEvalResult
        """
        max_thresh = self._find_max_threshold(probs_up)

        step = (max_thresh - 0.50) / 3 if max_thresh > 0.50 else 0.0
        thresholds = [round(0.50 + step * i, 4) for i in range(self.n_thresholds)]

        metrics_list: List[ThresholdMetrics] = []
        for t in thresholds:
            m = self._compute_threshold_metrics(probs_up, hard_labels, log_returns, t)
            metrics_list.append(m)

        best_ev = max((m.ev_score for m in metrics_list), default=0.0)

        return EpochEvalResult(
            threshold_metrics=metrics_list,
            max_threshold=max_thresh,
            best_ev=best_ev,
            val_loss=val_loss,
        )

    def is_statistically_valid(self, result: EpochEvalResult) -> bool:
        """True nếu ngưỡng L4 có đủ min_signals tín hiệu."""
        if not result.threshold_metrics:
            return False
        return result.threshold_metrics[-1].total_signals >= self.min_signals

    def format_summary(self, result: EpochEvalResult) -> str:
        """Tạo chuỗi log tóm tắt kết quả evaluation."""
        parts = [str(m) for m in result.threshold_metrics]
        composite = result.composite_score()
        return (
            f"MaxTh={result.max_threshold:.2f} | EV_composite={composite*10000:.2f}pip\n"
            + "  " + " | ".join(parts)
        )
