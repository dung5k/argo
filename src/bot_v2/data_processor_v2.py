import os
import numpy as np
import pandas as pd


class V2DataProcessor:
    """Xử lý dữ liệu đầu vào cho mô hình AI: Feature Engineering → Scale → Filter → Tensor.

    Trách nhiệm duy nhất: biến đổi raw DataFrame từ MT5 thành tensor 3D cho Inference Engine.
    Mỗi bước xử lý được tách thành hàm riêng để unit-test độc lập.
    """

    def __init__(self, scaler_path: str, inference_feats: list, window_size: int = 60, log_callback=None):
        self.scaler_path = scaler_path
        self.inference_feats = inference_feats
        self.window_size = window_size
        self.log_callback = log_callback or print
        self.pipeline = None
        self.log_callback(
            f"[DataProcessor] Khởi tạo | scaler={os.path.basename(scaler_path)} "
            f"| window={window_size} | n_feats={len(inference_feats)}"
        )

    # -------------------------------------------------------------------------
    # INIT PIPELINE (lazy)
    # -------------------------------------------------------------------------

    def _init_pipeline(self) -> bool:
        """Khởi tạo FeaturePipelineV2 (lazy – chỉ làm 1 lần khi cần)."""
        self.log_callback(f"[DataProcessor] 🔧 Khởi tạo FeaturePipelineV2 từ {self.scaler_path}...")
        import sys
        safe_script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if safe_script_dir not in sys.path:
            sys.path.insert(0, safe_script_dir)

        try:
            from src.training_v2.feature_pipeline_v2 import FeaturePipelineV2
            data_dir = os.path.dirname(self.scaler_path)
            self.pipeline = FeaturePipelineV2(target_prefix="INFERENCE", data_dir=data_dir)
            self.pipeline._scaler_path = self.scaler_path
            self.pipeline.load_scaler()
            self.log_callback("[DataProcessor] ✅ FeaturePipelineV2 sẵn sàng.")
            return True
        except Exception as e:
            self.log_callback(f"[DataProcessor] ❌ Không thể khởi tạo FeaturePipelineV2: {e}")
            return False

    # -------------------------------------------------------------------------
    # STEP 1 – Feature Engineering
    # -------------------------------------------------------------------------

    def run_feature_engineering(self, raw_df: pd.DataFrame) -> tuple:
        """Chạy feature engineering tĩnh (log return, indicator...) trên raw OHLCV DataFrame.

        Returns: (fe_df, error_message) – error_message là None nếu thành công.
        """
        self.log_callback(
            f"[DataProcessor] 📐 Bước 1 – Feature Engineering | input rows={len(raw_df)} cols={len(raw_df.columns)}"
        )
        try:
            from src.core import feature_engineering as fe

            if "XAUUSD_close" in raw_df.columns:
                fe.TARGET_PREFIX = "XAUUSD"

            fe_df, _ = fe.create_stationary_features(raw_df.copy(), is_live=True, apply_scaling=False)
            fe_df = fe_df.dropna()
            self.log_callback(f"[DataProcessor] ✅ Feature Engineering xong | rows={len(fe_df)} cols={len(fe_df.columns)}")

            if len(fe_df) < self.window_size:
                msg = f"Không đủ nến: cần {self.window_size}, chỉ có {len(fe_df)} sau FeatEng."
                self.log_callback(f"[DataProcessor] ⚠️ {msg}")
                return None, msg

            return fe_df, None
        except ImportError as e:
            msg = f"Import feature_engineering thất bại: {e}"
            self.log_callback(f"[DataProcessor] ❌ {msg}")
            return None, msg
        except Exception as e:
            msg = f"Lỗi khi chạy Feature Engineering: {e}"
            self.log_callback(f"[DataProcessor] ❌ {msg}")
            return None, msg

    # -------------------------------------------------------------------------
    # STEP 2 – Scale
    # -------------------------------------------------------------------------

    def scale_features(self, fe_df: pd.DataFrame) -> tuple:
        """Áp dụng Quantile Transform / Pipeline Scale lên DataFrame đã fe.

        Returns: (scaled_df, error_message)
        """
        self.log_callback(f"[DataProcessor] 📏 Bước 2 – Scale | input rows={len(fe_df)}")
        if self.pipeline is None:
            if not self._init_pipeline():
                return None, "Pipeline V2 Init Failed"
        try:
            scaled_df = self.pipeline.transform(fe_df)

            # Giữ lại is_imputed_flag nếu có (không đưa vào scaler nhưng cần cho Dataset filter)
            if 'is_imputed_flag' in fe_df.columns:
                scaled_df['is_imputed_flag'] = fe_df['is_imputed_flag'].reindex(scaled_df.index).fillna(0)
            else:
                scaled_df['is_imputed_flag'] = 0.0

            self.log_callback(
                f"[DataProcessor] ✅ Scale xong | rows={len(scaled_df)} cols={len(scaled_df.columns)}"
            )
            return scaled_df, None
        except Exception as e:
            msg = f"Lỗi Scale Pipeline: {e}"
            self.log_callback(f"[DataProcessor] ❌ {msg}")
            return None, msg

    # -------------------------------------------------------------------------
    # STEP 3 – Filter & Align Columns
    # -------------------------------------------------------------------------

    def filter_and_align(self, scaled_df: pd.DataFrame) -> tuple:
        """Lọc đúng cột mà Model yêu cầu (inference_feats), fill 0 nếu thiếu.

        Returns: (final_df, error_message)
        """
        if not self.inference_feats:
            self.log_callback("[DataProcessor] ℹ️ Không có inference_feats → dùng toàn bộ columns từ pipeline.")
            final_df = scaled_df.copy()
        else:
            missing = [c for c in self.inference_feats if c not in scaled_df.columns]
            if missing:
                self.log_callback(
                    f"[DataProcessor] ⚠️ Thiếu {len(missing)} cột: {missing[:5]}{'...' if len(missing) > 5 else ''}. Auto fill zeros."
                )
                for col in missing:
                    scaled_df[col] = 0.0
            final_df = scaled_df[self.inference_feats].copy()

        final_df = final_df.replace([np.inf, -np.inf], 0).fillna(0)
        self.log_callback(
            f"[DataProcessor] ✅ Filter & Align xong | final cols={len(final_df.columns)} rows={len(final_df)}"
        )
        return final_df, None

    # -------------------------------------------------------------------------
    # STEP 4 – Extract Window & Convert to Tensor
    # -------------------------------------------------------------------------

    def to_tensor(self, final_df: pd.DataFrame):
        """Trích đoạn window cuối và chuyển thành Tensor 3D (1, Win, Feat).

        Returns: (tensor, error_message)
        """
        window_df = final_df.iloc[-self.window_size:]
        self.log_callback(
            f"[DataProcessor] 🔢 Bước 4 – to_tensor | window shape={window_df.shape}"
        )
        try:
            import torch
            tensor = torch.tensor(window_df.values, dtype=torch.float32).unsqueeze(0)
            self.log_callback(f"[DataProcessor] ✅ Tensor shape: {tuple(tensor.shape)}")
            return tensor, None
        except Exception as e:
            # Fallback cho môi trường test không có torch đầy đủ
            self.log_callback(f"[DataProcessor] ⚠️ torch.tensor lỗi ({e}), trả về numpy array.")
            return window_df.values, None

    # -------------------------------------------------------------------------
    # PUBLIC ENTRY POINT
    # -------------------------------------------------------------------------

    def ingest_and_scale(self, raw_df: pd.DataFrame) -> tuple:
        """Pipeline tổng hợp: raw_df → Feature Eng → Scale → Filter → Tensor.

        Returns: (tensor, error_message) – tensor=None nếu có lỗi bất kỳ bước nào.
        """
        self.log_callback(
            f"[DataProcessor] ===== 🚀 Bắt đầu Pipeline | input={len(raw_df)} rows ====="
        )

        fe_df, err = self.run_feature_engineering(raw_df)
        if err:
            return None, err

        scaled_df, err = self.scale_features(fe_df)
        if err:
            return None, err

        final_df, err = self.filter_and_align(scaled_df)
        if err:
            return None, err

        tensor, err = self.to_tensor(final_df)
        if err:
            return None, err

        self.log_callback("[DataProcessor] ===== ✅ Pipeline hoàn tất thành công =====")
        return tensor, None
