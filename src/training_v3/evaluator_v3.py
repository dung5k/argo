"""
evaluator_v3.py — WinRate & Loss Evaluator V3
====================================================
Phiên bản đánh giá chuyên dụng cho Dữ liệu V3 (Không có log_returns).
Tập trung vào tổng đếm tỷ lệ Win Rate thuần túy và Penalty mất cân bằng.
"""

import torch
from dataclasses import dataclass, field
from typing import List

@dataclass
class ThresholdMetricsV3:
    threshold: float
    total_signals: int
    win_rate: float
    n_buy: int = 0
    n_sell: int = 0
    balanced_score: float = 0.0  # Điểm đánh giá (phạt nếu tỷ lệ Buy/Sell lệch quá lớn)

    def __str__(self) -> str:
        b_ratio = min(self.n_buy, self.n_sell) / max(1, max(self.n_buy, self.n_sell))
        return (
            f">={self.threshold*100:.0f}%: "
            f"WR={self.win_rate*100:.1f}% | "
            f"Score={self.balanced_score:.3f} | "
            f"N={self.total_signals} ({self.n_buy}B/{self.n_sell}S Bal:{b_ratio:.2f})"
        )

@dataclass
class EpochEvalResultV3:
    threshold_metrics: List[ThresholdMetricsV3] = field(default_factory=list)
    max_threshold: float = 0.50
    best_score: float = 0.0
    val_loss: float = float("inf")
    val_mse: float = float("inf")

    def composite_score(self) -> float:
        """Score tổng hợp dựa trên độ tự tin của 2 ngưỡng cao nhất (nếu có đủ 4 ngưỡng)"""
        if len(self.threshold_metrics) < 4:
            if not self.threshold_metrics: return 0.0
            return max(m.balanced_score for m in self.threshold_metrics)
        # Sử dụng Score của ngưỡng L3 (Index 2) và L4 (Index 3)
        l3 = self.threshold_metrics[2].balanced_score
        l4 = self.threshold_metrics[3].balanced_score
        return (1.4 * l3 + 1.0 * l4) / 2.4


class WinRateEvaluatorV3:
    def __init__(self, min_signals: int = 30, n_thresholds: int = 4):
        self.min_signals = min_signals
        self.n_thresholds = n_thresholds

    def _find_max_threshold(self, prob_sell: torch.Tensor, prob_buy: torch.Tensor) -> float:
        max_thresh = 0.50
        for t_int in range(99, 51, -1):
            t = t_int / 100.0
            n_buy  = (prob_buy > t).sum().item()
            n_sell = (prob_sell > t).sum().item()
            if (n_buy + n_sell) >= self.min_signals:
                max_thresh = t
                break
        return max_thresh

    def _compute_metrics(self, prob_sell: torch.Tensor, prob_buy: torch.Tensor, hard_labels: torch.Tensor, threshold: float) -> ThresholdMetricsV3:
        buy_mask  = prob_buy > threshold
        sell_mask = prob_sell > threshold

        # Target classes: 0=Sell, 1=Sideway/Hold, 2=Buy
        correct_buy  = buy_mask  & (hard_labels == 2)
        correct_sell = sell_mask & (hard_labels == 0)

        n_buy = buy_mask.sum().item()
        n_sell = sell_mask.sum().item()
        n_signals = n_buy + n_sell
        n_correct = correct_buy.sum().item() + correct_sell.sum().item()

        win_rate = n_correct / n_signals if n_signals > 0 else 0.0

        # Áp dụng phạt Mất Cân Bằng (Balance Penalty)
        score = win_rate
        if n_signals > 0:
            balance_ratio = min(n_buy, n_sell) / max(1, max(n_buy, n_sell))
            # Nếu 1 chiều cực liệt (0%), thì ratio=0 -> x0.6 (phạt cực mạnh)
            balance_factor = 0.6 + 0.4 * balance_ratio
            score = win_rate * balance_factor

        return ThresholdMetricsV3(
            threshold=threshold,
            total_signals=n_signals,
            n_buy=n_buy,
            n_sell=n_sell,
            win_rate=win_rate,
            balanced_score=score
        )

    def evaluate(self, logits: torch.Tensor, hard_labels: torch.Tensor, val_loss: float, val_mse: float) -> EpochEvalResultV3:
        # logits.shape = [Batch, 3] -> Class 0=Sell, 1=Hold, 2=Buy
        probs = torch.softmax(logits, dim=1)
        prob_sell = probs[:, 0]
        prob_buy = probs[:, 2]

        max_thresh = self._find_max_threshold(prob_sell, prob_buy)
        step = (max_thresh - 0.50) / 3 if max_thresh > 0.50 else 0.0
        thresholds = [round(0.50 + step * i, 4) for i in range(self.n_thresholds)]

        metrics_list = []
        for t in thresholds:
            m = self._compute_metrics(prob_sell, prob_buy, hard_labels, t)
            metrics_list.append(m)

        best_score = max((m.balanced_score for m in metrics_list), default=0.0)

        return EpochEvalResultV3(
            threshold_metrics=metrics_list,
            max_threshold=max_thresh,
            best_score=best_score,
            val_loss=val_loss,
            val_mse=val_mse
        )

    def format_summary(self, result: EpochEvalResultV3) -> str:
        parts = [str(m) for m in result.threshold_metrics]
        composite = result.composite_score()
        return (
            f"V3 Score [{composite:.3f}] - Loss(MSE:{result.val_mse:.4f}/CE:{result.val_loss-result.val_mse:.4f})\n"
            + "  " + " | ".join(parts)
        )
