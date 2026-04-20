import os
import sys
import numpy as np
import pandas as pd
import joblib

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3

class V3DataProcessor:
    """Xử lý dữ liệu đầu vào cho mô hình AI V3: Feature Engineering V3 → Scale → Tensor.
    """
    def __init__(self, scaler_path: str, inference_feats: list, window_size: int = 60, config: dict = None, log_callback=None):
        self.scaler_path = scaler_path
        self.inference_feats = inference_feats
        self.window_size = window_size
        self.config = config or {}
        self.log_callback = log_callback or print
        self.fe = None
        self.saved_column_order = None  # Thứ tự cột lúc Training (nếu có)
        self.log_callback(
            f"[DataProcessorV3] Khởi tạo | scaler={os.path.basename(scaler_path)} "
            f"| window={window_size} | n_feats={len(inference_feats)}"
        )

    def _init_fe(self) -> bool:
        if self.fe is not None:
            return True
            
        self.log_callback(f"[DataProcessorV3] 🔧 Khởi tạo FeatureEngineeringV3 từ {self.scaler_path}...")
        try:
            target_prefix = self.config.get('TARGET_PREFIX', 'XAUUSD')
            fe_cfg = self.config.get('FEATURE_ENGINEERING', {})
            macro_features = fe_cfg.get('MACRO_FEATURES', {})
            
            self.fe = FeatureEngineeringV3(target_prefix=target_prefix, macro_features=macro_features)
            
            # Load scaler (hỗ trợ cả format cũ và mới)
            raw_pickle = joblib.load(self.scaler_path)
            if isinstance(raw_pickle, dict) and "scaler" in raw_pickle:
                # Format mới: dict {scaler, column_order}
                self.fe.scaler = raw_pickle["scaler"]
                self.saved_column_order = raw_pickle.get("column_order", None)
                self.log_callback(f"[DataProcessorV3] 📐 Column order loaded: {len(self.saved_column_order)} cột")
            else:
                # Format cũ: chỉ có scaler object
                self.fe.scaler = raw_pickle
                self.saved_column_order = None
                self.log_callback("[DataProcessorV3] ⚠️ Scaler format cũ (không có column_order). Dùng thứ tự mặc định.")
            self.fe.is_fitted = True
            
            self.log_callback("[DataProcessorV3] ✅ FeatureEngineeringV3 sẵn sàng.")
            return True
        except Exception as e:
            self.log_callback(f"[DataProcessorV3] ❌ Không thể khởi tạo FeatureEngineeringV3: {e}")
            import traceback
            self.log_callback(traceback.format_exc())
            return False

    def ingest_and_scale(self, raw_df: pd.DataFrame) -> tuple:
        self.log_callback(f"[DataProcessorV3] ===== 🚀 Bắt đầu Pipeline V3 | input={len(raw_df)} rows =====")

        if not self._init_fe():
            return None, "Lỗi khởi tạo FeatureEngineeringV3"

        if len(raw_df) < self.window_size:
            msg = f"Không đủ nến raw: có {len(raw_df)}, cần ít nhất {self.window_size}."
            self.log_callback(f"[DataProcessorV3] ⚠️ {msg}")
            return None, msg

        # 1. Feature Engineering
        try:
            fe_df = self.fe.process_features(raw_df)
            self.log_callback(f"[DataProcessorV3] ✅ Phân tách tĩnh xong | col={fe_df.shape[1]}")
        except Exception as e:
            msg = f"Lỗi Feature Engineering: {e}"
            self.log_callback(f"[DataProcessorV3] ❌ {msg}")
            return None, msg

        # 2. Scale
        try:
            scaled_df = self.fe.transform_scaler(fe_df)
            self.log_callback(f"[DataProcessorV3] ✅ Scale xong | rows={len(scaled_df)} cols={len(scaled_df.columns)}")
        except Exception as e:
            msg = f"Lỗi Áp dụng Scaler: {e}"
            self.log_callback(f"[DataProcessorV3] ❌ {msg}")
            return None, msg
            
        if len(scaled_df) < self.window_size:
            msg = f"Sau FE & Drop NaN chỉ còn {len(scaled_df)} nến, không đủ {self.window_size}."
            self.log_callback(f"[DataProcessorV3] ⚠️ {msg}")
            return None, msg

        # 3. Khớp Khối Dữ Liệu Toán Học — ÉP THỨ TỰ CỘT KHỚP VỚI TRAINING
        if self.saved_column_order:
            # Dùng thứ tự cột chính xác từ lúc Training (đã lưu trong scaler pickle)
            available = set(scaled_df.columns)
            final_cols = [c for c in self.saved_column_order if c in available]
            # Nếu có cột thiếu, log cảnh báo
            missing = [c for c in self.saved_column_order if c not in available]
            if missing:
                self.log_callback(f"[DataProcessorV3] ⚠️ Thiếu {len(missing)} cột so với Training: {missing[:5]}")
        else:
            # Fallback: format cũ — dùng thứ tự từ DataFrame (rủi ro)
            valid_scaled_feats = self.inference_feats
            static_context_feats = ['hour_sin', 'hour_cos', 'is_asian', 'is_london', 'is_ny', 'rsi_14_scaled']
            allowed_features = set(valid_scaled_feats).union(set(static_context_feats))
            final_cols = [c for c in scaled_df.columns if c in allowed_features]
        
        final_df = scaled_df[final_cols].copy()
        
        final_df.replace([np.inf, -np.inf], 0, inplace=True)
        final_df.ffill(inplace=True)  # Ưu tiên giá trị gần nhất trước khi fill 0
        final_df.fillna(0, inplace=True)

        # 4. Trích Window cuối + to Tensor
        window_df = final_df.iloc[-self.window_size:]
        self.log_callback(f"[DataProcessorV3] 🔢 Bước 4 – to_tensor | window shape={window_df.shape}")
        
        try:
            import torch
            tensor = torch.tensor(window_df.values, dtype=torch.float32).unsqueeze(0)
            self.log_callback(f"[DataProcessorV3] ===== ✅ Pipeline hoàn tất thành công | {tuple(tensor.shape)} =====")
            return tensor, None
        except Exception as e:
            self.log_callback(f"[DataProcessorV3] ⚠️ torch.tensor lỗi ({e})")
            return None, str(e)
