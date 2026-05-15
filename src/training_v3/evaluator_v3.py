"""
evaluator_v3.py — WinRate & Loss Evaluator V3
====================================================
Phiên bản đánh giá chuyên dụng cho Dữ liệu V3 (Không có log_returns).
Tập trung vào tổng đếm tỷ lệ Win Rate thuần túy và Penalty mất cân bằng.
"""

import torch
import numpy as np
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
    tus_score: float = 0.0  # Time Under Stress / Total Units Scaled

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
    max_threshold: float = 0.53
    best_score: float = 0.0
    val_loss: float = float("inf")
    val_mse: float = float("inf")
    val_ce: float = float("inf")

    def composite_score(self) -> float:
        """Score tổng hợp dựa trên độ tự tin của 2 ngưỡng cao nhất (nếu có đủ 4 ngưỡng)"""
        if len(self.threshold_metrics) < 4:
            if not self.threshold_metrics: return 0.0
            return max(m.balanced_score for m in self.threshold_metrics)
        # Sử dụng Score của ngưỡng L3 (Index 2) và L4 (Index 3)
        l3 = self.threshold_metrics[2].balanced_score
        l4 = self.threshold_metrics[3].balanced_score
        return (1.4 * l3 + 1.0 * l4) / 2.4

    def format_summary(self) -> str:
        parts = [str(m) for m in self.threshold_metrics]
        composite = self.composite_score()
        return (
            f"V3 Score [{composite:.3f}] - Loss(MSE:{self.val_mse:.4f}/CE:{self.val_loss-self.val_mse:.4f})\n"
            + "  " + " | ".join(parts)
        )


class WinRateEvaluatorV3:
    def __init__(self, min_signals: int = 30, n_thresholds: int = 4,
                 freq_min_N: int = 80, freq_max_N: int = 1000):
        self.min_signals  = min_signals
        self.n_thresholds = n_thresholds
        # Frequency penalty params
        # min_N: dưới ngưỡng này → under-trading, bị phạt
        # max_N: trên ngưỡng này → over-trading, bị phạt
        self.freq_min_N = freq_min_N
        self.freq_max_N = freq_max_N

    @staticmethod
    def calculate_frequency_penalty(total_signals: int, min_N: int = 80, max_N: int = 1000) -> float:
        """
        Hàm phạt số lượng lệnh: trả về hệ số nhân trong [0.0, 1.0].
        - Vùng [→min_N, max_N]: không bị phạt -→ nhân 1.0
        - Dưới min_N (under-trading): hệ số = total / min_N
        - Trên max_N (over-trading)   : hệ số = max_N / total
        """
        if total_signals <= 0:
            return 0.0
        if total_signals < min_N:
            return total_signals / min_N          # e.g. 20/80 = 0.25
        if total_signals > max_N:
            return max_N / total_signals          # e.g. 1000/5000 = 0.20
        return 1.0                                # Vùng lý tưởng, không phạt

    def _find_max_threshold(self, prob_sell: torch.Tensor, prob_buy: torch.Tensor) -> float:
        max_thresh = 0.53
        
        buy_arr = prob_buy.cpu().numpy()
        sell_arr = prob_sell.cpu().numpy()
        seq_len = prob_buy.shape[0]
        hold_bars = 12 # Dùng 12 nến (trung bình) vì không có nhãn để biết chính xác
        
        for t_int in range(99, 53, -1):
            t = t_int / 100.0
            
            # Cần đếm số tín hiệu hợp lệ qua Fast Filter
            n_sig = 0
            next_free = 0
            for i in range(seq_len):
                if i < next_free: continue
                is_buy = buy_arr[i] > t
                is_sell = sell_arr[i] > t
                if (is_buy and not is_sell) or (is_sell and not is_buy):
                    n_sig += 1
                    next_free = i + hold_bars
                    
            if n_sig >= self.min_signals:
                max_thresh = t
                break
        return max_thresh

    def _compute_metrics(self, prob_sell: torch.Tensor, prob_buy: torch.Tensor, hard_labels: torch.Tensor, threshold: float, prices: torch.Tensor = None, tp_pips: float = 10.0, sl_pips: float = 10.0, pip_size: float = 0.01) -> ThresholdMetricsV3:
        buy_mask  = prob_buy > threshold
        sell_mask = prob_sell > threshold
        
        n_buy = 0
        n_sell = 0
        n_correct = 0
        
        # Mô phỏng Fast Simulator
        max_hold_bars = 20
        fast_hit_bars = 6
        loss_bars = 12
        next_free_bar = 0
        seq_len = prob_buy.shape[0]
        
        # Đưa tensor về CPU numpy/list để lặp cho nhanh
        buy_arr = buy_mask.cpu().numpy()
        sell_arr = sell_mask.cpu().numpy()
        lbl_arr = hard_labels.cpu().numpy()
        p_arr = prices.cpu().numpy() if prices is not None else None
        
        has_prices = p_arr is not None and np.any(p_arr > 0)
        
        for i in range(seq_len):
            if i < next_free_bar:
                continue
            
            is_buy = buy_arr[i]
            is_sell = sell_arr[i]
            
            if is_buy and not is_sell:
                n_buy += 1
                if has_prices:
                    entry_price = p_arr[i, 0]
                    if entry_price <= 0:
                        hit_bars = max_hold_bars
                    else:
                        tp_price = entry_price + (tp_pips * pip_size)
                        sl_price = entry_price - (sl_pips * pip_size)
                        hit_win = False
                        hit_bars = max_hold_bars
                        for j in range(1, p_arr.shape[1]):
                            future_price = p_arr[i, j]
                            if future_price <= 0: break
                            if future_price >= tp_price:
                                hit_win = True
                                hit_bars = j
                                break
                            elif future_price <= sl_price:
                                hit_win = False
                                hit_bars = j
                                break
                        if hit_win: n_correct += 1
                    next_free_bar = i + hit_bars
                else:
                    if lbl_arr[i] == 1:
                        n_correct += 1
                        next_free_bar = i + fast_hit_bars
                    elif lbl_arr[i] == 0:
                        next_free_bar = i + loss_bars
                    else:
                        next_free_bar = i + max_hold_bars
                        
            elif is_sell and not is_buy:
                n_sell += 1
                if has_prices:
                    entry_price = p_arr[i, 0]
                    if entry_price <= 0:
                        hit_bars = max_hold_bars
                    else:
                        tp_price = entry_price - (tp_pips * pip_size)
                        sl_price = entry_price + (sl_pips * pip_size)
                        hit_win = False
                        hit_bars = max_hold_bars
                        for j in range(1, p_arr.shape[1]):
                            future_price = p_arr[i, j]
                            if future_price <= 0: break
                            if future_price <= tp_price:
                                hit_win = True
                                hit_bars = j
                                break
                            elif future_price >= sl_price:
                                hit_win = False
                                hit_bars = j
                                break
                        if hit_win: n_correct += 1
                    next_free_bar = i + hit_bars
                else:
                    if lbl_arr[i] == 0:
                        n_correct += 1
                        next_free_bar = i + fast_hit_bars
                    elif lbl_arr[i] == 1:
                        next_free_bar = i + loss_bars
                    else:
                        next_free_bar = i + max_hold_bars

        n_signals = n_buy + n_sell
        win_rate = n_correct / n_signals if n_signals > 0 else 0.0

        # Áp dụng phạt Mất Cân Bằng (Balance Penalty)
        score = win_rate
        if n_signals > 0:
            balance_ratio = min(n_buy, n_sell) / max(1, max(n_buy, n_sell))
            # Nếu 1 chiều cực liệt (0%), thì ratio=0 -> x0.6 (phạt cực mạnh)
            balance_factor = 1.0 + 0.0 * balance_ratio
            score = win_rate * balance_factor

            # Áp dụng phạt Số Lượng Lệnh (Frequency Penalty)
            # → Chống under-trading (chỉ bắn vài lệnh, WR 100%) và over-trading (spam lệnh, dính spread)
            freq_factor = self.calculate_frequency_penalty(
                total_signals=n_signals,
                min_N=self.freq_min_N,
                max_N=self.freq_max_N
            )
            score = score * freq_factor

        tus_score = 1.0 - abs(n_buy - n_sell) / n_signals if n_signals > 0 else 0.0

        return ThresholdMetricsV3(
            threshold=threshold,
            total_signals=n_signals,
            n_buy=n_buy,
            n_sell=n_sell,
            win_rate=win_rate,
            balanced_score=score,
            tus_score=tus_score
        )

    def evaluate(self, logits: torch.Tensor, hard_labels: torch.Tensor, val_loss: float, val_mse: float, val_ce: float = float("inf"), prices: torch.Tensor = None, tp_pips: float = 10.0, sl_pips: float = 10.0, pip_size: float = 0.01) -> EpochEvalResultV3:
        # logits.shape = [Batch, 3] -> Class 0=Sell, 1=Buy, 2=Sideway
        
        # Đảm bảo trung bình 2 lệnh/ngày. Giả định trung bình 1 phiên có 400 nến (phút).
        val_size = logits.shape[0]
        val_days = max(1.0, val_size / 400.0)
        dynamic_min_N = int(val_days * 2.0)
        self.freq_min_N = dynamic_min_N
        
        probs = torch.softmax(logits, dim=1)
        prob_sell = probs[:, 0]
        prob_buy = probs[:, 1]

        max_thresh = self._find_max_threshold(prob_sell, prob_buy)
        
        if max_thresh > 0.54:
            step = (max_thresh - 0.53) / (self.n_thresholds - 1)
            thresholds = [round(0.53 + step * i, 4) for i in range(self.n_thresholds)]
        else:
            thresholds = [0.53, 0.68, 0.84, 0.99] # Mặc định giãn đều nếu không có tín hiệu cao
            max_thresh = 0.99
        metrics_list = []
        for t in thresholds:
            m = self._compute_metrics(prob_sell, prob_buy, hard_labels, t, prices=prices, tp_pips=tp_pips, sl_pips=sl_pips, pip_size=pip_size)
            metrics_list.append(m)

        best_score = max((m.balanced_score for m in metrics_list), default=0.0)

        return EpochEvalResultV3(
            threshold_metrics=metrics_list,
            max_threshold=max_thresh,
            best_score=best_score,
            val_loss=val_loss,
            val_mse=val_mse,
            val_ce=val_ce
        )


