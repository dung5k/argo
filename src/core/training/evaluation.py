"""
Evaluation helpers.

Trách nhiệm: Tính threshold tối ưu, WinRate, strategy scores — pure functions.
Input : tensor xác suất + nhãn
Output: thresholds, wrs, totals, scores — không có side effects
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import torch


def find_max_threshold(probs: torch.Tensor, min_signals: int) -> float:
    """
    Tìm threshold cao nhất sao cho tổng số tín hiệu BUY+SELL >= min_signals.

    Args:
        probs      : Tensor 1D xác suất BUY (output softmax[:, 1]).
        min_signals: Số tín hiệu tối thiểu để threshold hợp lệ.

    Returns:
        Threshold tốt nhất trong [0.50, 0.99]. Trả 0.50 nếu không đủ tín hiệu.
    """
    for t_int in range(99, 50, -1):
        t = t_int / 100.0
        n_buy  = (probs > t).sum().item()
        n_sell = (probs < (1.0 - t)).sum().item()
        if (n_buy + n_sell) >= min_signals:
            return t
    return 0.50


def build_thresholds(max_thresh: float, n_steps: int = 4) -> List[float]:
    """
    Tạo danh sách n_steps thresholds đều nhau từ 0.50 đến max_thresh.

    Args:
        max_thresh: Threshold tối đa tìm được từ find_max_threshold.
        n_steps   : Số bước (mặc định 4 = L1..L4).

    Returns:
        List[float] gồm n_steps phần tử.
    """
    step = (max_thresh - 0.50) / (n_steps - 1) if max_thresh > 0.50 else 0
    return [round(0.50 + step * i, 4) for i in range(n_steps)]


def compute_winrates(
    probs: torch.Tensor,
    labels: torch.Tensor,
    thresholds: List[float],
) -> Tuple[List[float], List[int]]:
    """
    Tính WinRate tại mỗi threshold.

    Args:
        probs     : Tensor 1D xác suất BUY.
        labels    : Tensor 1D nhãn thực tế (0=SELL, 1=BUY).
        thresholds: Danh sách threshold cần tính.

    Returns:
        (wrs, totals) — wrs[i] là WinRate tại thresholds[i], totals[i] là tổng tín hiệu.
    """
    wrs: List[float] = []
    totals: List[int] = []
    for t in thresholds:
        lo = 1.0 - t
        buy_mask  = probs > t
        sell_mask = probs < lo
        n = buy_mask.sum().item() + sell_mask.sum().item()
        correct = (
            (labels[buy_mask] == 1).sum().item()
            + (labels[sell_mask] == 0).sum().item()
        )
        wrs.append(correct / n if n > 0 else 0.0)
        totals.append(int(n))
    return wrs, totals


def calc_strategy_scores(wrs: List[float], avg_val_loss: float) -> Dict[str, float]:
    """
    Tính điểm xếp hạng cho từng chiến thuật lưu checkpoint.

    Args:
        wrs         : WinRate tại 4 mức threshold (wrs[0]=L1..wrs[3]=L4).
        avg_val_loss: Val loss trung bình epoch hiện tại.

    Returns:
        Dict[strategy_name -> score]. Score cao hơn = tốt hơn.
    """
    return {
        "L3_1.4_L4_1.0": (1.4 * wrs[2] + 1.0 * wrs[3]) / 2.4,
        "L3_1.1_L4_1.0": (1.1 * wrs[2] + 1.0 * wrs[3]) / 2.1,
        "BEST_VLOSS":     -avg_val_loss,
    }
