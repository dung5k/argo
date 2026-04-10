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

    def __init__(self, features_df: pd.DataFrame, targets_df: pd.DataFrame, window_size: int, session: str = "all"):
        self.features_tensor = torch.FloatTensor(features_df.values.copy())
        self.labels_tensor   = torch.LongTensor(targets_df["target"].values.copy())
        self.window_size     = window_size
        
        valid_start = window_size - 1
        total_len = len(self.features_tensor)
        
        if session != "all":
            hours = features_df.index.hour.values
            if session.lower() == "asian":
                mask = (hours < 8)
            elif session.lower() == "european":
                mask = (hours >= 8) & (hours < 13)
            elif session.lower() == "ny":
                mask = (hours >= 13)
            else:
                mask = np.ones_like(hours, dtype=bool)
                
            valid_indices = np.where(mask)[0]
            self.indices = valid_indices[valid_indices >= valid_start]
        else:
            self.indices = np.arange(valid_start, total_len)

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        target_idx = self.indices[idx]
        start_idx = target_idx - self.window_size + 1
        x = self.features_tensor[start_idx : target_idx + 1]
        y = self.labels_tensor[target_idx]
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
    session: str = "all",
) -> Tuple[DataLoader, DataLoader, TimeSeriesDataset, TimeSeriesDataset]:
    """
    Tạo DataLoader cho train và validation lọc theo session.

    Returns:
        (train_loader, val_loader, train_dataset, val_dataset)
        Trả về cả dataset để có thể reload khi batch_size thay đổi.
    """
    train_ds = TimeSeriesDataset(train_features, train_targets, window_size, session)
    val_ds   = TimeSeriesDataset(val_features,   val_targets,   window_size, session)
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False)
    return train_dl, val_dl, train_ds, val_ds
