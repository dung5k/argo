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
    def __init__(self, scaler_path: str, inference_feats: list, window_size: int = 60, config: dict = None, log_callback=None, model_input_dim: int = None):
        self.scaler_path = scaler_path
        self.inference_feats = inference_feats
        self.window_size = window_size
        self.config = config or {}
        self.log_callback = log_callback or print
        self.model_input_dim = model_input_dim
        self.fe = None
        self.saved_column_order = None  # Thứ tự cột lúc Training (nếu có)
        self.log_callback(
            f"[DataProcessorV3] Khởi tạo | scaler={os.path.basename(scaler_path)} "
            f"| window={window_size} | n_feats={len(inference_feats)} | model_input_dim={model_input_dim}"
        )

    def _init_fe(self) -> bool:
        if self.fe is not None:
            return True
            
        self.log_callback(f"[DataProcessorV3] 🔧 Khởi tạo FeatureEngineeringV3 từ {self.scaler_path}...")
        try:
            target_prefix = self.config.get('TARGET_PREFIX', 'XAUUSD')
            fe_cfg = self.config.get('FEATURE_ENGINEERING', {})
            macro_features = fe_cfg.get('MACRO_FEATURES', {})
            
            # Tự động cắt tỉa các Mã Vĩ Mô không nằm trong bộ Não (backward compatibility)
            filtered_macro = {}
            for m_sym, m_cols in macro_features.items():
                m_sym_lower = m_sym.lower()
                # Nếu inference_feats là list strings (từ scaler), ta lọc.
                # Nếu là integers (auto-detect từ weights), ta giữ hết để đảm bảo không bị thiếu.
                if not self.inference_feats or not isinstance(self.inference_feats[0], str):
                    filtered_macro[m_sym] = m_cols
                elif any(m_sym_lower in feat.lower() for feat in self.inference_feats if isinstance(feat, str)):
                    filtered_macro[m_sym] = m_cols
                else:
                    self.log_callback(f"[DataProcessorV3] ⚠️ Bỏ qua mã Vĩ Mô '{m_sym}' vì không có trong bộ Não (Scaler).")
            
            self.fe = FeatureEngineeringV3(
                target_prefix=target_prefix, 
                macro_features=filtered_macro,
                mtf_windows=fe_cfg.get('MTF_WINDOWS', None),
                order_flow=fe_cfg.get('ORDER_FLOW', False),
                vol_regime=fe_cfg.get('VOL_REGIME', False),
                crypto_mode=fe_cfg.get('CRYPTO_MODE', False),
                zero_noise_target=fe_cfg.get('ZERO_NOISE_TARGET', False)
            )
            
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

        self.log_callback(f"[DataProcessorV3] Raw columns: {list(raw_df.columns)}")

        if len(raw_df) < self.window_size:
            msg = f"Không đủ nến raw: có {len(raw_df)}, cần ít nhất {self.window_size}."
            self.log_callback(f"[DataProcessorV3] ⚠️ {msg}")
            return None, msg

        # 1. Feature Engineering
        try:
            fe_df = self.fe.process_features(raw_df)
            self.log_callback(f"[DataProcessorV3] ✅ Phân tách tĩnh xong | col={fe_df.shape[1]}")
            self.log_callback(f"[DataProcessorV3] FE columns (first 20): {list(fe_df.columns)[:20]}")
        except Exception as e:
            msg = f"Lỗi Feature Engineering: {e}"
            self.log_callback(f"[DataProcessorV3] ❌ {msg}")
            return None, msg

        # [VÁ LỖI #0] Fix động các tính năng bị thiếu TRƯỚC khi đưa vào Scaler để tránh lỗi scikit-learn
        if "volume" not in fe_df.columns:
            vol_cols = [col for col in fe_df.columns if 'volume' in col.lower()]
            if vol_cols:
                fe_df["volume"] = fe_df[vol_cols[0]]
            else:
                fe_df["volume"] = 0.0
                
        if "spread" not in fe_df.columns:
            fe_df["spread"] = 0.0

        # 2. Scale — transform_scaler tự xử lý: scale features nó biết, passthrough phần còn lại
        try:
            n_model = len(self.inference_feats)
            scaled_df = self.fe.transform_scaler(fe_df)
            self.log_callback(f"[DataProcessorV3] ✅ Scale xong | rows={len(scaled_df)} cols={len(scaled_df.columns)}")
            
            # Auto-trim: cắt cho khớp model input_dim
            if len(scaled_df.columns) > n_model and isinstance(self.inference_feats[0], int):
                self.log_callback(f"[DataProcessorV3] ⚠️ Auto-trim: {len(scaled_df.columns)} cols → {n_model} (model input_dim)")
                scaled_df = scaled_df.iloc[:, :n_model]
        except Exception as e:
            msg = f"Lỗi Áp dụng Scaler: {e}"
            self.log_callback(f"[DataProcessorV3] ❌ {msg}")
            return None, msg
            
        if len(scaled_df) < self.window_size:
            msg = f"Sau FE & Drop NaN chỉ còn {len(scaled_df)} nến, không đủ {self.window_size}."
            self.log_callback(f"[DataProcessorV3] ⚠️ {msg}")
            return None, msg

        # 3. Khớp Khối Dữ Liệu Toán Học — ÉP THỨ TỰ CỘT KHỚP VỚI TRAINING
        # Bỏ qua khi inference_feats là integers (auto-trim mode từ model weights)
        if isinstance(self.inference_feats[0], int):
            final_cols = list(scaled_df.columns)
        elif self.saved_column_order:
            available = set(scaled_df.columns)
            missing = [c for c in self.saved_column_order if c not in available]
            
            if missing:
                for c in missing:
                    if c == "volume" and f"{self.config.get('TARGET_PREFIX', '')}_volume" in scaled_df.columns:
                        scaled_df["volume"] = scaled_df[f"{self.config.get('TARGET_PREFIX', '')}_volume"]
                        available.add("volume")
                    elif c == "spread":
                        scaled_df["spread"] = 0.0
                        available.add("spread")
            
            missing = [c for c in self.saved_column_order if c not in available]
            if missing:
                # [VÁ LỖI #1] Fail-fast ngay lập tức - không tự ý cắt gọt tensor
                msg = f"Thiếu {len(missing)} cột so với Training: {missing[:5]}... TỪ CHỐI SUY LUẬN!"
                self.log_callback(f"[DataProcessorV3] ❌ FATAL: {msg}")
                return None, msg
            final_cols = self.saved_column_order
        else:
            # Fallback: format scaler cũ
            final_cols = list(scaled_df.columns)
            
            # Nếu có model_input_dim và scaler cũ không lưu column_order, tự động cắt các tính năng thừa ở đuôi (thường là tính năng mới thêm vào fe_v3 sau này)
            if self.model_input_dim and len(final_cols) > self.model_input_dim:
                self.log_callback(f"[DataProcessorV3] ⚠️ Tự động tỉa cột từ {len(final_cols)} xuống {self.model_input_dim} cho khớp model weights cũ.")
                final_cols = final_cols[:self.model_input_dim]

            # [HACK] Khả năng tương thích ngược cho LTC Asian (run_20260422_143008_v3) expect 36 features
            elif len(self.inference_feats) == 25 and len(final_cols) == 45:
                static_context_feats = ['hour_sin', 'hour_cos', 'minute_sin', 'minute_cos', 'is_asian', 'is_london', 'is_ny', 'rsi_14_scaled', 'rsi_5_scaled', 'body_pct', 'adx_normalized']
                allowed_features = set(self.inference_feats).union(set(static_context_feats))
                final_cols = [c for c in scaled_df.columns if c in allowed_features]

        final_df = scaled_df[final_cols].copy()

        # [VÁ LỖI #2] Xử lý NaN đồng nhất với Training (chỉ ffill tối đa 3 nến, không fillna(0))
        final_df.replace([np.inf, -np.inf], np.nan, inplace=True)
        final_df.ffill(limit=3, inplace=True)

        # 4. Trích Window cuối + to Tensor
        window_df = final_df.iloc[-self.window_size:]

        # Kiểm tra rác lần cuối — đồng nhất với `if np.isnan(window).any(): continue` bên Training
        if window_df.isnull().values.any():
            nan_cols = window_df.columns[window_df.isnull().any()].tolist()
            msg = f"Window 60 nến cuối vẫn còn NaN sau ffill(limit=3) tại {nan_cols[:3]}. Từ chối đưa vào Mạng Nơ-ron!"
            self.log_callback(f"[DataProcessorV3] ❌ {msg}")
            return None, msg

        self.log_callback(f"[DataProcessorV3] 🔢 Bước 4 – to_tensor | window shape={window_df.shape}")

        try:
            import torch
            tensor = torch.tensor(window_df.values, dtype=torch.float32).unsqueeze(0)
            self.log_callback(f"[DataProcessorV3] ===== ✅ Pipeline hoàn tất thành công | {tuple(tensor.shape)} =====")
            return tensor, None
        except Exception as e:
            self.log_callback(f"[DataProcessorV3] ⚠️ torch.tensor lỗi ({e})")
            return None, str(e)
