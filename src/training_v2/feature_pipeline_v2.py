"""
feature_pipeline_v2.py — Feature Pipeline V2
=============================================
Kế thừa toàn bộ logic từ feature_engineering.py (V1), chỉ thay thế:

    StandardScaler (Z-score)  →  QuantileTransformer (output_distribution='normal')

Lý do toán học:
    Log Returns tài chính có phân phối đuôi dày (Leptokurtic / Fat-tails).
    StandardScaler giả định Gaussian → các sự kiện biến động mạnh tạo z-score > 10,
    gây tràn Softmax trong Transformer Attention.

    QuantileTransformer ép toàn bộ phân phối về Normal(0,1) thực sự,
    giới hạn outlier, giữ không gian vector đầu vào ổn định hình học.

Thay đổi so với V1:
    - Scaler: QuantileTransformer(output_distribution='normal')
    - Clip sau transform: np.clip(scaled_data, -3.5, 3.5)
    - Lưu file: scaler_v2.pkl (KHÔNG ghi đè scaler.pkl của V1)
    - Metadata: feature_meta_{TARGET_PREFIX}_v2.json
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import QuantileTransformer


# Số lượng quantile tối thiểu (giảm với dataset nhỏ)
_MIN_N_QUANTILES = 100
_MAX_N_QUANTILES = 1000

# Clip range sau khi transform (phòng thủ outlier còn sót)
_CLIP_RANGE = 3.5


class FeaturePipelineV2:
    """
    Pipeline tiền xử lý features dùng QuantileTransformer.

    Parameters
    ----------
    target_prefix : str
        Tiền tố mã giao dịch, ví dụ 'XAUUSD' hoặc 'EURUSD'.
    data_dir : str
        Đường dẫn thư mục data/ để đọc/lưu scaler và metadata.
    clip_range : float
        Giới hạn clip sau khi transform. Mặc định 3.5.
    """

    def __init__(
        self,
        target_prefix: str,
        data_dir: str,
        clip_range: float = _CLIP_RANGE,
    ):
        self.target_prefix = target_prefix
        self.data_dir = data_dir
        self.clip_range = clip_range
        self.scaler: QuantileTransformer | None = None
        self._feature_names: list = []  # Lưu tên cột khi fit (thay feature_names_in_)
        self._scaler_path = os.path.join(data_dir, "scaler_v2.pkl")
        self._meta_path = os.path.join(
            data_dir, f"feature_meta_{target_prefix}_v2.json"
        )

    def _make_scaler(self, n_samples: int) -> QuantileTransformer:
        n_quantiles = max(_MIN_N_QUANTILES, min(_MAX_N_QUANTILES, n_samples))
        return QuantileTransformer(
            output_distribution="normal",
            n_quantiles=n_quantiles,
            subsample=max(n_samples, 200_000),
            random_state=42,
        )

    def fit_transform(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit scaler mới trên tập train và transform.

        Parameters
        ----------
        feature_df : pd.DataFrame
            DataFrame features đã qua stationary transform (log returns, v.v.).

        Returns
        -------
        pd.DataFrame
            DataFrame đã scaled, cùng shape và index với input.
        """
        n_samples, n_features = feature_df.shape
        print(
            f"[PipelineV2] Fit QuantileTransformer: {n_samples:,} samples × "
            f"{n_features} features (n_quantiles={min(_MAX_N_QUANTILES, n_samples)})"
        )

        self._feature_names = list(feature_df.columns)  # Lưu tên cột trước khi fit
        self.scaler = self._make_scaler(n_samples)
        scaled_data = self.scaler.fit_transform(feature_df.values)

        # Clip phòng thủ: triệt tiêu outlier còn sót sau QuantileTransform
        n_clipped = np.sum(np.abs(scaled_data) > self.clip_range)
        scaled_data = np.clip(scaled_data, -self.clip_range, self.clip_range)

        print(
            f"[PipelineV2] Clip [{-self.clip_range}, {self.clip_range}]: "
            f"{n_clipped:,} giá trị đã được giới hạn ({n_clipped / scaled_data.size * 100:.3f}%)"
        )

        # Lưu scaler kèm tên cột vào cùng 1 dict để tái sử dụng khi load
        save_obj = {"scaler": self.scaler, "feature_names": self._feature_names}
        joblib.dump(save_obj, self._scaler_path)
        print(f"[PipelineV2] Đã lưu scaler: {self._scaler_path}")

        # Lưu metadata
        xau_cols = [c for c in feature_df.columns if c.startswith(self.target_prefix)]
        meta = {
            "num_target_features": len(xau_cols),
            "total_features": n_features,
            "target_prefix": self.target_prefix,
            "scaler_type": "QuantileTransformer",
            "clip_range": self.clip_range,
            "feature_names": self._feature_names,
        }
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)

        return pd.DataFrame(scaled_data, index=feature_df.index, columns=feature_df.columns)

    def transform(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform dữ liệu Live dùng scaler đã fit.

        Parameters
        ----------
        feature_df : pd.DataFrame
            DataFrame features chưa scaled.

        Returns
        -------
        pd.DataFrame
            DataFrame đã scaled và clipped.

        Raises
        ------
        RuntimeError
            Nếu chưa fit hoặc chưa load scaler.
        """
        if self.scaler is None:
            raise RuntimeError(
                "Scaler chưa được fit hoặc load. Gọi fit_transform() hoặc load_scaler() trước."
            )

        # Auto-align cột theo _feature_names đã lưu khi fit
        expected_cols = self._feature_names
        missing = [c for c in expected_cols if c not in feature_df.columns]
        if missing:
            print(f"[PipelineV2] Zero-pad {len(missing)} cột thiếu: {missing[:3]}...")
            pad = pd.DataFrame(0.0, index=feature_df.index, columns=missing)
            feature_df = pd.concat([feature_df, pad], axis=1)

        extra = [c for c in feature_df.columns if c not in expected_cols]
        if extra:
            print(f"[PipelineV2] Loại bỏ {len(extra)} cột thừa: {extra[:3]}...")

        feature_df = feature_df[expected_cols]

        scaled_data = self.scaler.transform(feature_df.values)
        scaled_data = np.clip(scaled_data, -self.clip_range, self.clip_range)

        return pd.DataFrame(scaled_data, index=feature_df.index, columns=feature_df.columns)

    def load_scaler(self) -> "FeaturePipelineV2":
        """Load scaler đã lưu từ file scaler_v2.pkl."""
        if not os.path.exists(self._scaler_path):
            raise FileNotFoundError(f"Không tìm thấy scaler: {self._scaler_path}")
        save_obj = joblib.load(self._scaler_path)
        if isinstance(save_obj, dict) and "scaler" in save_obj:
            self.scaler = save_obj["scaler"]
            self._feature_names = save_obj.get("feature_names", [])
        else:
            # Backward compat: file cũ chỉ lưu scaler trực tiếp
            self.scaler = save_obj
            self._feature_names = []
        print(f"[PipelineV2] Đã load scaler từ: {self._scaler_path}")
        return self

    def load_metadata(self) -> dict:
        """Đọc metadata của pipeline."""
        if not os.path.exists(self._meta_path):
            raise FileNotFoundError(f"Không tìm thấy metadata: {self._meta_path}")
        with open(self._meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
