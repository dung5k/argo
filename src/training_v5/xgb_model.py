import os
import pickle
import numpy as np
import xgboost as xgb
import pandas as pd

class VolatilityRiskManager:
    """
    Quản lý rủi ro dựa trên biến động (ATR Z-score).
    Thay vì dùng ngưỡng tĩnh, ngưỡng giao dịch được nội suy từ Z-Score.
    """
    def __init__(self, window=20, min_threshold=0.6, max_threshold=0.95):
        self.window = window
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold

    def get_dynamic_threshold(self, atr_zscore: np.ndarray) -> np.ndarray:
        # ATR Z-score càng cao (thị trường càng biến động) -> Ngưỡng đòi hỏi càng khắt khe
        # Normalize zscore -> threshold
        z = np.clip(atr_zscore, -2, 2)
        norm_z = (z + 2) / 4.0 # 0 to 1
        thresholds = self.min_threshold + norm_z * (self.max_threshold - self.min_threshold)
        return thresholds


class SelectiveXGBoost:
    """
    Selective Prediction Engine (V5) sử dụng Gradient Boosting kết hợp Volatility Risk Manager.
    Không đoán bừa: Mọi xác suất dự đoán không vượt Threshold ĐỘNG đều trả về nhãn 2 (Sideway/Neutral).
    """
    def __init__(self, xgb_params: dict):
        self.xgb_params = xgb_params
        self.model = None
        self.risk_manager = VolatilityRiskManager()
        
    def fit(self, X_train: np.ndarray, y_train: np.ndarray, 
            X_val: np.ndarray = None, y_val: np.ndarray = None):
        
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        evals = [(dtrain, 'train')]
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val)
            evals.append((dval, 'eval'))
            
        print("🎄 Bắt đầu trồng cây XGBoost (Quy luật Phân tập)...")
        num_boost_round = self.xgb_params.pop('n_estimators', 100)
        
        self.model = xgb.train(
            params=self.xgb_params,
            dtrain=dtrain,
            num_boost_round=num_boost_round,
            evals=evals,
            early_stopping_rounds=50,
            verbose_eval=10
        )
        print("✅ Hoàn tất XGBoost Training!")

    def predict_selective(self, X: np.ndarray, atr_zscores: np.ndarray = None) -> np.ndarray:
        """
        Dự báo Selective sử dụng dynamic threshold từ Risk Manager.
        """
        if self.model is None:
            raise ValueError("Mô hình chưa được train.")
            
        dtest = xgb.DMatrix(X)
        probs = self.model.predict(dtest) # shape: (N, 3)
        
        preds = np.full(len(X), 2) # Trạng thái Abstain mặc định
        
        if atr_zscores is None:
            thresholds = np.full(len(X), 0.90) # Fallback to static
        else:
            thresholds = self.risk_manager.get_dynamic_threshold(atr_zscores)
        
        # BUY
        preds[probs[:, 1] >= thresholds] = 1
        # SELL
        preds[probs[:, 0] >= thresholds] = 0
        
        return preds, probs
        
    def save(self, file_path: str):
        if self.model is not None:
            self.model.save_model(file_path)
            
    def load(self, file_path: str):
        self.model = xgb.Booster()
        self.model.load_model(file_path)

    @classmethod
    def from_pretrained(cls, file_path: str, params: dict = None):
        instance = cls(params or {})
        instance.load(file_path)
        return instance
