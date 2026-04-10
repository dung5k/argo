"""Unit tests cho data_pipeline module."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'core'))

import numpy as np
import pandas as pd
import pytest
import torch


def _make_df(n=300, cols=None, tz="Asia/Ho_Chi_Minh"):
    """Tạo DataFrame giả với DatetimeIndex."""
    if cols is None:
        cols = [f"f{i}" for i in range(5)]
    idx = pd.date_range("2024-01-01", periods=n, freq="1min", tz=tz)
    df  = pd.DataFrame(np.random.randn(n, len(cols)), index=idx, columns=cols)
    return df


def _make_targets(n=300, tz="Asia/Ho_Chi_Minh"):
    idx = pd.date_range("2024-01-01", periods=n, freq="1min", tz=tz)
    return pd.DataFrame({"target": np.random.randint(0, 2, n)}, index=idx)


class TestSplitTrainVal:
    def test_split_returns_correct_sizes(self):
        from core.training.data_pipeline import split_train_val
        df  = _make_df(200)
        tgt = _make_targets(200)
        ts = pd.Timestamp("2024-01-01", tz="UTC")
        te = pd.Timestamp("2024-01-02", tz="UTC")
        vs = te
        ve = pd.Timestamp("2024-01-03", tz="UTC")
        tr_f, tr_t, vl_f, vl_t = split_train_val(df, tgt, ts, te, vs, ve)
        assert len(tr_f) > 0
        assert len(vl_f) > 0
        assert len(tr_f) + len(vl_f) <= 200

    def test_train_val_no_overlap(self):
        from core.training.data_pipeline import split_train_val
        df  = _make_df(200)
        tgt = _make_targets(200)
        ts = pd.Timestamp("2024-01-01", tz="UTC")
        te = pd.Timestamp("2024-01-02", tz="UTC")
        vs = te
        ve = pd.Timestamp("2024-01-03", tz="UTC")
        tr_f, _, vl_f, _ = split_train_val(df, tgt, ts, te, vs, ve)
        tr_utc = tr_f.tz_convert("UTC")
        vl_utc = vl_f.tz_convert("UTC")
        # Không có index trùng nhau
        common = set(tr_utc.index) & set(vl_utc.index)
        assert len(common) == 0


class TestComputeClassWeights:
    def test_balanced_returns_equal_weights(self):
        from core.training.data_pipeline import compute_class_weights
        labels = np.array([0, 1, 0, 1, 0, 1], dtype=np.int64)
        w = compute_class_weights(labels, torch.device("cpu"))
        assert abs(w[0].item() - w[1].item()) < 1e-5

    def test_imbalanced_minority_gets_higher_weight(self):
        from core.training.data_pipeline import compute_class_weights
        # 90% sell, 10% buy → buy weight phải cao hơn
        labels = np.array([0]*90 + [1]*10, dtype=np.int64)
        w = compute_class_weights(labels, torch.device("cpu"))
        assert w[1].item() > w[0].item()

    def test_all_same_class_no_crash(self):
        from core.training.data_pipeline import compute_class_weights
        labels = np.zeros(100, dtype=np.int64)
        w = compute_class_weights(labels, torch.device("cpu"))
        assert w[1].item() == 1.0   # fallback 1.0 khi n_buy = 0


class TestMakeDataloaders:
    def test_returns_correct_types(self):
        from core.training.data_pipeline import make_dataloaders
        from torch.utils.data import DataLoader
        feat = _make_df(200, cols=[f"f{i}" for i in range(5)])
        tgt  = _make_targets(200)
        train_dl, val_dl, _, _ = make_dataloaders(feat, tgt, feat, tgt, 60, 32)
        assert isinstance(train_dl, DataLoader)
        assert isinstance(val_dl, DataLoader)

    def test_batch_shapes(self):
        from core.training.data_pipeline import make_dataloaders
        feat = _make_df(200, cols=[f"f{i}" for i in range(5)])
        tgt  = _make_targets(200)
        train_dl, _, _, _ = make_dataloaders(feat, tgt, feat, tgt, 60, 32)
        batch_x, batch_y = next(iter(train_dl))
        assert batch_x.shape[1] == 60   # window_size
        assert batch_x.shape[2] == 5    # num_features
        assert batch_y.ndim == 1
