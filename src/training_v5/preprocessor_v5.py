import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

class PreprocessorV5:
    """
    Tiền xử lý dữ liệu vi mô (Micro features) cho XGBoost.
    Cách hoạt động giống V4 (Tạo Sliding Window) 
    NHƯNG bước cuối cùng Flatten (Cán phẳng) ma trận (N, 20, F) -> (N, 20*F) để làm Dữ liệu bảng cho Decision Trees.
    """
    def __init__(self, config: dict):
        self.config = config
        self.cfg_engine = config.get("V5_XGB_ENGINE", {})
        self.leader_assets = self.cfg_engine.get("LEADER_ASSETS", {})
        self.window_size = self.cfg_engine.get("BAR_WINDOW", 20)
        self.target_symbol = config.get("TARGET_SYMBOL", "LTCUSDT")
        
        self.scaler = RobustScaler()
        self.is_fitted = False
        
    def calculate_features(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()
        
        # Tiền xử lý cho TẤT CẢ các Leader Assets + Target
        all_symbols = list(self.leader_assets.keys())
        if self.target_symbol not in all_symbols:
            all_symbols.append(self.target_symbol)
            
        for sym in all_symbols:
            source = self.leader_assets.get(sym, {}).get("source", "BINANCE").upper()
            close_col = f"{sym}_close"
            vol_col = f"{sym}_volume" if source == "BINANCE" else f"{sym}_tick_volume"
            
            if close_col not in df.columns: continue
            df[f'{sym}_log_ret'] = np.log(df[close_col] / df[close_col].shift(1))
            
            # Tính RVOL (Volume tương đối theo SMA20)   
            if vol_col in df.columns:
                sma_vol = df[vol_col].rolling(20).mean()
                df[f'{sym}_rvol'] = df[vol_col] / sma_vol.replace(0, 1)
        
        df = df.replace([np.inf, -np.inf], np.nan).ffill().bfill()
        return df

    def fit_transform(self, df_raw: pd.DataFrame):
        df_feat = self.calculate_features(df_raw)
        
        # Chọn lựa các feature cột theo Config
        selected_cols = []
        for sym, cfg in self.leader_assets.items():
            for f in cfg.get("features", []):
                col = f"{sym}_{f}"
                if col in df_feat.columns:
                    selected_cols.append(col)
                    
        # Nếu target_symbol không có trong leader assets, thêm thủ công
        if self.target_symbol not in self.leader_assets:
            target_feat = [f"{self.target_symbol}_log_ret", f"{self.target_symbol}_rvol"]
            for col in target_feat:
                if col in df_feat.columns and col not in selected_cols:
                    selected_cols.append(col)
                    
        print(f"  [Prep V5] Bốc tách {len(selected_cols)} vi mô: {selected_cols}")
        data_matrix = df_feat[selected_cols].values
        
        # Scaling
        scaled_data = self.scaler.fit_transform(data_matrix)
        self.is_fitted = True
        
        # Tạo Sliding Windows
        X, valid_indices = [], []
        timestamps = df_feat.index
        
        for i in range(self.window_size - 1, len(scaled_data)):
            window = scaled_data[i - self.window_size + 1 : i + 1]
            if not np.isnan(window).any():
                X.append(window.flatten()) # Flatten (20, 5) -> (100) cho XGBoost
                valid_indices.append(timestamps[i])
                
        # Trả về numpy 2D (Samples, Features_Flattened)
        return np.array(X), np.array(valid_indices)

    def transform(self, df_raw: pd.DataFrame):
        if not self.is_fitted:
            raise ValueError("Scaler chưa được fit!")
            
        df_feat = self.calculate_features(df_raw)
        
        selected_cols = []
        for sym, cfg in self.leader_assets.items():
            for f in cfg.get("features", []):
                col = f"{sym}_{f}"
                if col in df_feat.columns:
                    selected_cols.append(col)
                    
        if self.target_symbol not in self.leader_assets:
            target_feat = [f"{self.target_symbol}_log_ret", f"{self.target_symbol}_rvol"]
            for col in target_feat:
                if col in df_feat.columns and col not in selected_cols:
                    selected_cols.append(col)
                    
        data_matrix = df_feat[selected_cols].values
        scaled_data = self.scaler.transform(data_matrix)
        
        X, valid_indices = [], []
        timestamps = df_feat.index
        
        for i in range(self.window_size - 1, len(scaled_data)):
            window = scaled_data[i - self.window_size + 1 : i + 1]
            if not np.isnan(window).any():
                X.append(window.flatten())
                valid_indices.append(timestamps[i])
                
        return np.array(X), np.array(valid_indices)
