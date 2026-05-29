import pandas as pd
import json

from src.training_v3.model_v3 import AAMT_Model
from src.core_v3.feature_engineering_v3 import FeatureEngineeringV3
from src.training_v3.inference_v3 import InferenceV3

class TradeBotV3Bridge:
    """
    Cầu nối giữa MT5 Live System và Thuật toán AI V3.
    """
    def __init__(self, config_path="workspaces/CFG_XAU_NY_V3_5/base_config.json", model_weights_path=None):
        # 1. Đọc Config
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.fe_cfg = self.config['FEATURE_ENGINEERING']
        self.bot_cfg = self.config['LIVE_BOT']
        
        # 2. Khởi tạo Môi trường Kỹ thuật (Features)
        self.feature_engine = FeatureEngineeringV3(target_prefix=self.config['TARGET_PREFIX'])
        # (Thực tế khi run live, scaler phải lôi file .pkl đã train ra load)
        # self.feature_engine.scaler = joblib.load('scaler_v3.pkl')
        # self.feature_engine.is_fitted = True
        
        # 3. Khởi tạo Mô hình (Architecture)
        train_cfg = self.config['TRAINING']
        self.model = AAMT_Model(
            input_dim=15, 
            seq_len=self.fe_cfg['WINDOW_SIZE'],
            d_model=train_cfg['D_MODEL'],
            nhead=train_cfg['N_HEAD'],
            num_layers=train_cfg['NUM_LAYERS'],
            num_classes=3
        )
        
        # if model_weights_path:
        #    self.model.load_state_dict(torch.load(model_weights_path))
            
        # 4. Khởi tạo Bức tường Lọc (Inference Filter)
        self.inference = InferenceV3(
            model=self.model,
            mse_threshold=self.bot_cfg['MSE_THRESHOLD_PERCENTILE'], # Điểm phân vị 70 của Loss
            prob_threshold=self.bot_cfg['MIN_PROBABILITY_THRESH'] # 0.63 hoặc 0.7
        )
        
    def live_predict_step(self, mt5_raw_df: pd.DataFrame):
        """
        Nhồi Dataframe M1 vào hàm này mỗi khi có nến mới.
        Yêu cầu df phải dài ít nhất 60 nến (WINDOW_SIZE)
        """
        if len(mt5_raw_df) < self.fe_cfg['WINDOW_SIZE']:
            return "CHƯA_ĐỦ_NẾN", 0.0, {}
            
        # Transform data raw -> Features V3
        df_features = self.feature_engine.process_features(mt5_raw_df)
        
        # Cắt đi đúng Cửa sổ 60 nến sau cùng (sát hiện tại nhất)
        df_features_window = df_features.iloc[-self.fe_cfg['WINDOW_SIZE']:]
        
        # Scale (phụ thuộc self.feature_engine.is_fitted)
        # df_scaled = self.feature_engine.transform_scaler(df_features_window)
        # Trong bot khung xương này ta bỏ qua báo còi scale để biểu diễn
        import torch
        tensor_input = torch.tensor(df_features_window.values).float().unsqueeze(0)
        
        # RA QUYẾT ĐỊNH XUYÊN 2 LỚP LỌC
        action, mse_loss, probs = self.inference.predict(tensor_input)
        
        print(f"[AAMT V3 Predict] Nhãn: {action} | Lỗi Kiến cấu (MSE): {mse_loss:.4f} | Prob: {probs}")
        return action, mse_loss, probs
