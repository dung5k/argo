"""
Data pipeline functions.

Trách nhiệm: Chia tập train/val, tính class weights, tạo DataLoader.
Tất cả hàm đều pure function — không có side effects, dễ unit test.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset


class TimeSeriesDataset(Dataset):
    """
    Dataset cho time-series window.

    Args:
        features_df: DataFrame features (indexed by datetime).
        targets_df : DataFrame targets với cột 'target'.
        window_size: Số nến trong mỗi cửa sổ.
    """

    def __init__(self, features_df: pd.DataFrame, targets_df: pd.DataFrame, window_size: int):
        self.features_tensor = torch.FloatTensor(features_df.values)
        self.labels_tensor   = torch.LongTensor(targets_df["target"].values)
        self.window_size     = window_size

    def __len__(self) -> int:
        return max(0, len(self.features_tensor) - self.window_size)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.features_tensor[idx : idx + self.window_size]
        y = self.labels_tensor[idx + self.window_size - 1]
        return x, y


def split_train_val(
    features: pd.DataFrame,
    targets: pd.DataFrame,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    val_start: pd.Timestamp,
    val_end: pd.Timestamp,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Chia features/targets thành tập train và validation theo time range.

    Args:
        features   : DataFrame features có DatetimeIndex với timezone.
        targets    : DataFrame targets có cột 'target'.
        train_start: Thời điểm bắt đầu train (UTC-aware).
        train_end  : Thời điểm kết thúc train (UTC-aware).
        val_start  : Thời điểm bắt đầu validate (UTC-aware).
        val_end    : Thời điểm kết thúc validate (UTC-aware).

    Returns:
        (train_features, train_targets, val_features, val_targets)
    """
    feat_utc = features.tz_convert("UTC")
    tgt_utc  = targets.tz_convert("UTC")

    train_mask = (feat_utc.index >= train_start) & (feat_utc.index < train_end)
    val_mask   = (feat_utc.index >= val_start)   & (feat_utc.index < val_end)

    return (
        feat_utc[train_mask], tgt_utc[train_mask],
        feat_utc[val_mask],   tgt_utc[val_mask],
    )


def compute_class_weights(labels: np.ndarray, device: torch.device) -> torch.Tensor:
    """
    Tính class weights đảo ngược (inverse frequency) cho CrossEntropyLoss.

    Args:
        labels: Mảng nhãn 0/1.
        device: Torch device.

    Returns:
        Tensor [w_sell, w_buy] — đã đưa lên device.
    """
    n_total = len(labels)
    n_buy   = int((labels == 1).sum())
    n_sell  = int((labels == 0).sum())
    w_sell  = n_total / (2.0 * n_sell) if n_sell > 0 else 1.0
    w_buy   = n_total / (2.0 * n_buy)  if n_buy  > 0 else 1.0
    return torch.tensor([w_sell, w_buy], dtype=torch.float32).to(device)


def make_dataloaders(
    train_features: pd.DataFrame,
    train_targets:  pd.DataFrame,
    val_features:   pd.DataFrame,
    val_targets:    pd.DataFrame,
    window_size: int,
    batch_size:  int,
) -> Tuple[DataLoader, DataLoader, TimeSeriesDataset, TimeSeriesDataset]:
    """
    Tạo DataLoader cho train và validation.

    Returns:
        (train_loader, val_loader, train_dataset, val_dataset)
        Trả về cả dataset để có thể reload khi batch_size thay đổi.
    """
    train_ds = TimeSeriesDataset(train_features, train_targets, window_size)
    val_ds   = TimeSeriesDataset(val_features,   val_targets,   window_size)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)
    return train_dl, val_dl, train_ds, val_ds
