import os
import pickle
import numpy as np
import xgboost as xgb

class SelectiveXGBoost:
    """
    Selective Prediction Engine (V5) sử dụng Gradient Boosting.
    Không đoán bừa: Mọi xác suất dự đoán không vượt Threshold đều trả về nhãn 2 (Sideway/Neutral).
    """
    def __init__(self, xgb_params: dict):
        self.xgb_params = xgb_params
        self.model = None
        
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

    def predict_selective(self, X: np.ndarray, threshold: float = 0.90) -> np.ndarray:
        """
        Dự báo Selective: 
        Nếu probability(UP) > threshold -> 1 (BUY)
        Nếu probability(DOWN) > threshold -> 0 (SELL)
        Còn lại -> 2 (Abstain/Sideway)
        """
        if self.model is None:
            raise ValueError("Mô hình chưa được train.")
            
        dtest = xgb.DMatrix(X)
        probs = self.model.predict(dtest) # shape: (N, 3)
        
        preds = np.full(len(X), 2) # Trạng thái Abstain mặc định
        
        preds[probs[:, 1] >= threshold] = 1 # BUY
        preds[probs[:, 0] >= threshold] = 0 # SELL
        
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
