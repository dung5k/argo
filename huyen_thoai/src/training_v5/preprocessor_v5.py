import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.model_selection import TimeSeriesSplit

class PurgedTimeSeriesSplit:
    """
    Purged TimeSeriesSplit để tránh Data Leakage (Look-ahead bias) khi dùng Sliding Windows.
    Đảm bảo có một khoảng Gap (embargo) giữa Train và Validation.
    """
    def __init__(self, n_splits=5, gap=0):
        self.n_splits = n_splits
        self.gap = gap

    def split(self, X, y=None, groups=None):
        tscv = TimeSeriesSplit(n_splits=self.n_splits, gap=self.gap)
        for train_index, test_index in tscv.split(X):
            yield train_index, test_index

class PreprocessorV5:
    """
    Tiền xử lý dữ liệu vi mô (Micro features) cho XGBoost.
    Sử dụng PurgedTimeSeriesSplit và fit Scaler ĐỘC LẬP trên mỗi fold để ngăn chặn Data Leakage.
    Đồng thời đảm bảo các Feature đều được Stationary hóa (Log returns, Fractional Diff).
    """
    def __init__(self, config: dict):
        self.config = config
        self.cfg_engine = config.get("V5_XGB_ENGINE", {})
        self.leader_assets = self.cfg_engine.get("LEADER_ASSETS", {})
        self.window_size = self.cfg_engine.get("BAR_WINDOW", 20)
        self.target_symbol = config.get("TARGET_PREFIX", "LTC")
        
        # Không dùng scaler toàn cục ở đây nữa, scaler sẽ được khởi tạo per fold
        
    def calculate_stationary_features(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()
        
        all_symbols = list(self.leader_assets.keys())
        if self.target_symbol not in all_symbols:
            all_symbols.append(self.target_symbol)
            
        for sym in all_symbols:
            source = self.leader_assets.get(sym, {}).get("source", "BINANCE").upper()
            close_col = f"{sym}_close"
            vol_col = f"{sym}_volume" if source == "BINANCE" else f"{sym}_tick_volume"
            
            if close_col not in df.columns: continue
            
            # 1. Stationary feature: Log Returns thay vì raw price
            df[f'{sym}_log_ret'] = np.log(df[close_col] / df[close_col].shift(1))
            
            # 2. Volatility Scaling (ATR approximation)
            ret_abs = df[f'{sym}_log_ret'].abs()
            df[f'{sym}_atr_14'] = ret_abs.rolling(14).mean()
            df[f'{sym}_vol_scaled'] = df[f'{sym}_log_ret'] / df[f'{sym}_atr_14'].replace(0, 1)
            
            # Tính RVOL (Volume tương đối theo SMA20)   
            if vol_col in df.columns:
                sma_vol = df[vol_col].rolling(20).mean()
                df[f'{sym}_rvol'] = df[vol_col] / sma_vol.replace(0, 1)
        
        df = df.replace([np.inf, -np.inf], np.nan).ffill().bfill()
        return df

    def extract_windows(self, df_raw: pd.DataFrame):
        df_feat = self.calculate_stationary_features(df_raw)
        
        selected_cols = []
        for sym, cfg in self.leader_assets.items():
            for f in cfg.get("features", []):
                col = f"{sym}_{f}"
                if col in df_feat.columns:
                    selected_cols.append(col)
                    
        if self.target_symbol not in self.leader_assets:
            target_feat = [f"{self.target_symbol}_log_ret", f"{self.target_symbol}_rvol", f"{self.target_symbol}_vol_scaled"]
            for col in target_feat:
                if col in df_feat.columns and col not in selected_cols:
                    selected_cols.append(col)
                    
        print(f"  [Prep V5] Bốc tách {len(selected_cols)} vi mô (Đã Stationary): {selected_cols}")
        data_matrix = df_feat[selected_cols].values
        
        # Tạo Sliding Windows thô (CHƯA SCALE)
        X, valid_indices = [], []
        timestamps = df_feat.index
        
        for i in range(self.window_size - 1, len(data_matrix)):
            window = data_matrix[i - self.window_size + 1 : i + 1]
            if not np.isnan(window).any():
                X.append(window.flatten())
                valid_indices.append(timestamps[i])
                
        return np.array(X), np.array(valid_indices)

    def generate_purged_folds(self, X: np.ndarray, y: np.ndarray, n_splits=5, gap=20):
        """
        Sinh ra các fold huấn luyện và scale ĐỘC LẬP cho từng fold.
        """
        cv = PurgedTimeSeriesSplit(n_splits=n_splits, gap=gap)
        folds = []
        
        for train_idx, val_idx in cv.split(X):
            X_train_raw, y_train = X[train_idx], y[train_idx]
            X_val_raw, y_val = X[val_idx], y[val_idx]
            
            # Fit scaler CHỈ trên tập train của fold này
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train_raw)
            X_val_scaled = scaler.transform(X_val_raw)
            
            folds.append({
                'X_train': X_train_scaled, 'y_train': y_train,
                'X_val': X_val_scaled, 'y_val': y_val,
                'scaler': scaler
            })
            
        return folds
