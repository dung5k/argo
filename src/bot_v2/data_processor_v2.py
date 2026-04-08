import os
import numpy as np
import pandas as pd

class V2DataProcessor:
    """Xử lý dữ liệu đầu vào: Feature Engineering và Biến đổi Lượng Tử (Quantile Transform) qua Pipeline V2"""
    
    def __init__(self, scaler_path: str, inference_feats: list, window_size: int = 60, log_callback=None):
        self.scaler_path = scaler_path
        self.inference_feats = inference_feats
        self.window_size = window_size
        self.log_callback = log_callback or print
        self.pipeline = None

    def _init_pipeline(self):
        """Khởi tạo FeaturePipelineV2 (Chỉ làm 1 lần)"""
        # Tránh lỗi module not found
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
            return True
        except Exception as e:
            self.log_callback(f"[DataProcessor] ❌ Không thể khởi tạo FeaturePipelineV2: {e}")
            return False

    def ingest_and_scale(self, raw_df: pd.DataFrame) -> tuple:
        """
        Nhận DataFrame gốc (từ MT5), tạo feature, scale và chuyển thành Tensor.
        Trả về (tensor_3d_numpy_array, error_message)
        """
        if self.pipeline is None:
            if not self._init_pipeline():
                return None, "Pipeline V2 Init Failed"
                
        try:
            # 1. Feature Engineering (Kế thừa Scaling từ V1, yêu cầu is_live=True để dùng chung scaler.pkl)
            try:
                from src.core import feature_engineering as fe
                fe_raw_df, _ = fe.create_stationary_features(raw_df.copy(), is_live=True)
            except ImportError:
                return None, "Import feature_engineering failed"
                
            # 2. Bỏ qua các hàng NaN do shift/rolling
            fe_raw_df = fe_raw_df.dropna()
            if len(fe_raw_df) < self.window_size:
                return None, f"Không đủ {self.window_size} nến gốc sau FeatEng (chỉ có {len(fe_raw_df)})."
                
            # 3. Scale Data theo Pipeline V2
            scaled_df = self.pipeline.transform(fe_raw_df)
            
            # Reattach is_imputed_flag because PipelineV2 drops it during transform (matching train_v2 logic)
            if 'is_imputed_flag' in fe_raw_df.columns:
                scaled_df['is_imputed_flag'] = fe_raw_df['is_imputed_flag'].loc[scaled_df.index]
            else:
                scaled_df['is_imputed_flag'] = 0.0
            
            # 4. Filter features khớp với Mạng
            if self.inference_feats:
                missing_cols = [c for c in self.inference_feats if c not in scaled_df.columns]
                if missing_cols:
                    # Fill missing macro data with 0 (Giả lập padding)
                    self.log_callback(f"[DataProcessor] Cảnh báo: Thiếu {len(missing_cols)} cột macro. Auto fill zeros.")
                    for col in missing_cols:
                        scaled_df[col] = 0.0
                        
                final_df = scaled_df[self.inference_feats].copy()
            else:
                # Nếu Mây không cung cấp List, mặc định dùng trọn vẹn kết quả do PipelineV2 định tuyến (luôn chuẩn xác)
                final_df = scaled_df.copy()
            final_df = final_df.replace([np.inf, -np.inf], 0).fillna(0)
            
            # 5. Extract the window
            window_df = final_df.iloc[-self.window_size:]
            
            # 6. Transform to Tensor form (1, Window, NumFeat)
            try:
                import torch
                tensor_seq = torch.tensor(window_df.values, dtype=torch.float32).unsqueeze(0)
                return tensor_seq, None
            except Exception as e:
                # For testing environments where strict torch isn't fully set up with pandas
                return window_df.values, None
            
        except Exception as e:
            return None, f"Lỗi DataProcessor: {str(e)}"
