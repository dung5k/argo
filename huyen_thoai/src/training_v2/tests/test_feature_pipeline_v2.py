"""
test_feature_pipeline_v2.py — Unit tests cho FeaturePipelineV2
"""

import sys
import os
import json
import tempfile
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from src.training_v2.feature_pipeline_v2 import FeaturePipelineV2


@pytest.fixture
def tmp_dir(tmp_path):
    return str(tmp_path)


@pytest.fixture
def sample_df():
    """DataFrame giả lập với phân phối fat-tail."""
    np.random.seed(42)
    n = 500
    idx = pd.date_range("2025-01-01", periods=n, freq="1min", tz="UTC")

    data = {
        "XAUUSD_close_log_ret": np.random.standard_t(df=3, size=n) * 0.001,  # fat-tail
        "XAUUSD_RSI": np.random.uniform(0, 100, n),
        "EURUSD_close_log_ret": np.random.normal(0, 0.0005, n),
        "macro_feature": np.random.normal(0, 1, n),
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def pipeline(tmp_dir):
    return FeaturePipelineV2(
        target_prefix="XAUUSD",
        data_dir=tmp_dir,
        clip_range=3.5,
    )


class TestFitTransform:
    def test_output_shape_unchanged(self, pipeline, sample_df):
        """Shape đầu ra phải giống đầu vào."""
        result = pipeline.fit_transform(sample_df)
        assert result.shape == sample_df.shape

    def test_output_index_unchanged(self, pipeline, sample_df):
        """Index không được thay đổi."""
        result = pipeline.fit_transform(sample_df)
        pd.testing.assert_index_equal(result.index, sample_df.index)

    def test_output_clipped_within_range(self, pipeline, sample_df):
        """Tất cả giá trị phải nằm trong [-3.5, 3.5]."""
        result = pipeline.fit_transform(sample_df)
        assert result.values.max() <= 3.5 + 1e-6, \
            f"Max = {result.values.max():.4f} vượt clip_range"
        assert result.values.min() >= -3.5 - 1e-6, \
            f"Min = {result.values.min():.4f} vượt clip_range"

    def test_output_no_nan_no_inf(self, pipeline, sample_df):
        """Không có NaN hay Inf sau transform."""
        result = pipeline.fit_transform(sample_df)
        assert not result.isna().any().any()
        assert not np.isinf(result.values).any()

    def test_scaler_saved(self, pipeline, sample_df, tmp_dir):
        """scaler_v2.pkl phải được lưu ra disk."""
        pipeline.fit_transform(sample_df)
        expected_path = os.path.join(tmp_dir, "scaler_v2.pkl")
        assert os.path.exists(expected_path), "scaler_v2.pkl không được tạo"

    def test_metadata_saved(self, pipeline, sample_df, tmp_dir):
        """feature_meta_XAUUSD_v2.json phải được tạo."""
        pipeline.fit_transform(sample_df)
        meta_path = os.path.join(tmp_dir, "feature_meta_XAUUSD_v2.json")
        assert os.path.exists(meta_path)

        with open(meta_path) as f:
            meta = json.load(f)
        assert "total_features" in meta
        assert meta["total_features"] == sample_df.shape[1]
        assert meta["scaler_type"] == "QuantileTransformer"

    def test_output_distribution_approximately_normal(self, pipeline, sample_df):
        """
        QuantileTransformer(output_distribution='normal') phải ép phân phối
        về gần Normal(0,1). Kiểm tra mean ≈ 0 và std ≈ 1 (sau clip).
        """
        result = pipeline.fit_transform(sample_df)
        col = "XAUUSD_close_log_ret"
        col_data = result[col].values

        mean_val = np.mean(col_data)
        std_val  = np.std(col_data)

        assert abs(mean_val) < 0.5, f"Mean {mean_val:.3f} không gần 0"
        # Sau clip ở ±3.5, std sẽ < 1 một chút
        assert 0.3 < std_val < 1.5, f"Std {std_val:.3f} không hợp lý"


class TestTransform:
    """Kiểm tra transform() sau khi fit."""

    def test_transform_consistent_with_fit_transform(self, pipeline, sample_df, tmp_dir):
        """
        Transform trên cùng dữ liệu sau khi fit phải cho kết quả gần giống fit_transform.
        (Không hoàn toàn bằng vì train/test split có thể khác.)
        """
        result_fit = pipeline.fit_transform(sample_df)

        # Load lại scaler và transform lại
        pipeline2 = FeaturePipelineV2("XAUUSD", tmp_dir)
        pipeline2.load_scaler()
        result_transform = pipeline2.transform(sample_df)

        # Kết quả phải xấp xỉ nhau
        np.testing.assert_allclose(
            result_fit.values, result_transform.values, atol=1e-5,
            err_msg="fit_transform và transform(load_scaler) phải nhất quán"
        )

    def test_transform_before_fit_raises(self, pipeline, sample_df):
        """transform() trước khi fit phải raise RuntimeError."""
        with pytest.raises(RuntimeError, match="Scaler chưa được fit"):
            pipeline.transform(sample_df)

    def test_transform_auto_pads_missing_columns(self, pipeline, sample_df, tmp_dir):
        """Cột thiếu trong live data phải được Zero-Pad thay vì crash."""
        pipeline.fit_transform(sample_df)

        # Tạo live data thiếu 1 cột
        live_df = sample_df.drop(columns=["macro_feature"])

        pipeline2 = FeaturePipelineV2("XAUUSD", tmp_dir)
        pipeline2.load_scaler()

        # Không được raise exception
        result = pipeline2.transform(live_df)
        assert result is not None

    def test_load_scaler_missing_file_raises(self, tmp_dir):
        """load_scaler() khi không có file phải raise FileNotFoundError."""
        pipeline = FeaturePipelineV2("MISSING", tmp_dir)
        with pytest.raises(FileNotFoundError, match="scaler_v2.pkl"):
            pipeline.load_scaler()


class TestComparisonWithStandardScaler:
    """So sánh hành vi của QuantileTransformer vs StandardScaler với fat-tail data."""

    def test_quantile_suppresses_outliers_better(self, pipeline, tmp_dir):
        """
        QuantileTransformer phải cho max absolute value nhỏ hơn StandardScaler
        khi có outliers (đặc trưng của fat-tail data).
        """
        from sklearn.preprocessing import StandardScaler

        np.random.seed(0)
        n = 200
        idx = pd.date_range("2025-01-01", periods=n, freq="1min", tz="UTC")
        # Thêm outlier cực lớn (fat-tail event)
        data = np.random.normal(0, 1, n)
        data[[10, 50, 150]] = [50.0, -80.0, 100.0]  # outliers thiên nga đen
        df = pd.DataFrame({"feature": data}, index=idx)

        # StandardScaler
        ss = StandardScaler()
        ss_scaled = ss.fit_transform(df.values)
        ss_max = np.abs(ss_scaled).max()

        # QuantileTransformer (pipeline V2)
        p = FeaturePipelineV2("XAUUSD", tmp_dir, clip_range=3.5)
        qt_scaled = p.fit_transform(df)
        qt_max = qt_scaled.abs().values.max()

        assert qt_max < ss_max, \
            f"QuantileTransformer ({qt_max:.2f}) phải < StandardScaler ({ss_max:.2f}) với outliers"
        assert qt_max <= 3.5, \
            f"QuantileTransformer phải bị clip tại 3.5, got {qt_max:.2f}"
