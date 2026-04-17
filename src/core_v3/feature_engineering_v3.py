import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

class FeatureEngineeringV3:
    """
    Module xử lý Feature Engineering chuẩn V3 AAMT.
    Tập trung vào tính toán 4 nhóm đặc trưng trực giao, loại bỏ nhiễu và dư thừa.
    """
    def __init__(self, target_prefix="XAUUSDm"):
        self.target_prefix = target_prefix
        self.scaler = RobustScaler()
        self.is_fitted = False
        
    def calculate_price_action(self, df, open_col, high_col, low_col, close_col):
        """Tính toán nhóm Hình thái giá: Log Returns và Bóng nến"""
        features = pd.DataFrame(index=df.index)
        
        # Log Returns (so với giá đóng cửa phiên trước để giữ tính liên tục)
        prev_close = df[close_col].shift(1)
        # Điền NaN đầu tiên bằng chính giá open của nến đó để tránh rách index
        prev_close = prev_close.bfill()
        
        # Cộng thêm epsilon nhỏ (1e-6) để tránh log(0) trong trường hợp giá không đổi hoặc lỗi dữ liệu
        features['log_return_open'] = np.log((df[open_col] / prev_close) + 1e-6)
        features['log_return_high'] = np.log((df[high_col] / prev_close) + 1e-6)
        features['log_return_low'] = np.log((df[low_col] / prev_close) + 1e-6)
        features['log_return_close'] = np.log((df[close_col] / prev_close) + 1e-6)
        
        # Wicks - Bóng nến (tính theo phần trăm thân nến hoặc theo spread nến)
        # Để tránh chia cho 0 khi nến Doji hoàn hảo (Open == Close), ta cộng epsilon
        candle_body = np.abs(df[close_col] - df[open_col]) + 1e-6
        
        # Bóng trên = (High - max(Open, Close)) / Body
        max_oc = np.maximum(df[open_col], df[close_col])
        features['upper_wick_pct'] = (df[high_col] - max_oc) / candle_body
        
        # Bóng dưới = (min(Open, Close) - Low) / Body
        min_oc = np.minimum(df[open_col], df[close_col])
        features['lower_wick_pct'] = (min_oc - df[low_col]) / candle_body
        
        return features
        
    def calculate_volatility(self, df, high_col, low_col, close_col, bb_period=20, atr_period=14):
        """Tính toán nhóm Biến động: ATR chuẩn hóa và Bollinger Band Width"""
        features = pd.DataFrame(index=df.index)
        
        # Tính True Range (TR)
        prev_close = df[close_col].shift(1).bfill()
        tr1 = df[high_col] - df[low_col]
        tr2 = np.abs(df[high_col] - prev_close)
        tr3 = np.abs(df[low_col] - prev_close)
        tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        
        # Tính Average True Range (ATR)
        atr = tr.rolling(window=atr_period, min_periods=1).mean()
        
        # Chuẩn hóa ATR theo mức giá hiện tại để nó invariant theo giá tuyệt đối
        features['atr_normalized'] = atr / (df[close_col] + 1e-6)
        
        # Tính Bollinger Band Width
        # Middle Band = 20-period SMA
        sma = df[close_col].rolling(window=bb_period, min_periods=1).mean()
        # Tính Standard Deviation
        rstd = df[close_col].rolling(window=bb_period, min_periods=1).std()
        rstd = rstd.bfill() # Xử lý NaN ở những nến đầu
        
        upper_band = sma + 2 * rstd
        lower_band = sma - 2 * rstd
        
        features['bb_width'] = (upper_band - lower_band) / (sma + 1e-6)
        
        return features
        
    def calculate_momentum(self, df, close_col, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9):
        """Tính toán nhóm Động lượng: RSI và MACD Histogram"""
        features = pd.DataFrame(index=df.index)
        
        # Tính RSI
        delta = df[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        
        rs = gain / (loss + 1e-6)
        rsi = 100 - (100 / (1 + rs))
        # Chuẩn hóa RSI về [-1, 1] cho Neural Network dễ học
        features['rsi_14_scaled'] = (rsi / 50.0) - 1.0
        
        # Tính MACD
        ema_fast = df[close_col].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = df[close_col].ewm(span=macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        # Dùng trực tiếp giá trị MACD Histogram vì nó đã dao động quanh 0, bước RobustScaler sẽ co giãn lại
        features['macd_hist'] = macd_hist
        
        return features
        
    def calculate_time_context(self, df):
        """Tính toán Ngữ cảnh thời gian: Sin/Cos mã hóa giờ, Cờ từng phiên giao dịch"""
        features = pd.DataFrame(index=df.index)
        
        # Yêu cầu df.index phải là dạng datetime và set Timezone chuẩn là UTC
        # Giả định df.index đã chuẩn hoá thành UTC khi merge data
        hour = df.index.hour
        
        # Cyclical Time Encoding
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)
        
        # One-Hot Encoding Phiên (Giờ tham chiếu theo chuẩn UTC)
        # Asian: 00:00 -> 07:00 UTC
        # London (Âu): 07:00 -> 12:30 UTC -> xấp xỉ 07:00 -> 12:59
        # NY (Mỹ): 13:00 -> 22:00 UTC
        
        features['is_asian'] = ((hour >= 0) & (hour < 7)).astype(float)
        features['is_london'] = ((hour >= 7) & (hour < 13)).astype(float)
        features['is_ny'] = ((hour >= 13) & (hour < 22)).astype(float)
        
        return features

    def process_features(self, df):
        """Hành trình nhào nặn gộp toàn bộ 4 nhánh tín hiệu"""
        # Xác định cột dựa trên target_prefix, dự phòng tên viết thường
        prefix = self.target_prefix.lower() if self.target_prefix.lower() + "_close" in map(str.lower, df.columns) else self.target_prefix
        
        # Lấy tên chính xác từ DF
        cols = {c.lower(): c for c in df.columns}
        try:
            open_col = cols[f"{prefix}_open".lower()]
            high_col = cols[f"{prefix}_high".lower()]
            low_col = cols[f"{prefix}_low".lower()]
            close_col = cols[f"{prefix}_close".lower()]
        except KeyError as e:
            raise KeyError(f"Không tìm đủ các cột OHLC cho mã {prefix}. Chi tiết lỗi: {e}")

        # Ráp các nhánh features
        f_pa = self.calculate_price_action(df, open_col, high_col, low_col, close_col)
        f_vol = self.calculate_volatility(df, high_col, low_col, close_col)
        f_mom = self.calculate_momentum(df, close_col)
        f_time = self.calculate_time_context(df)
        
        # Nối tất cả vào chung một khung
        final_features = pd.concat([f_pa, f_vol, f_mom, f_time], axis=1)
        
        # Xoá các giá trị NaN phát sinh do độ trễ rolling window của RSI/MACD (thường ở 30 row đầu tiên)
        final_features = final_features.bfill()
        
        return final_features
        
    def fit_transform_scaler(self, features_df):
        """Scale data trong lúc Training"""
        # Tránh đưa cột Time Context (sin/cos/vùng one-hot) vào scaler vì bản thân nó đã nằm trong biên [-1, 1] hoặc [0, 1]
        cols_to_scale = [c for c in features_df.columns if not c.startswith(('hour_', 'is_', 'rsi_14_scaled'))]
        
        scaled_data = features_df.copy()
        
        if cols_to_scale:
            scaled_vals = self.scaler.fit_transform(features_df[cols_to_scale])
            scaled_data[cols_to_scale] = scaled_vals
            self.is_fitted = True
            
        return scaled_data
        
    def transform_scaler(self, features_df):
        """Scale data trong lúc Live Inference"""
        if not self.is_fitted:
            raise ValueError("Scaler chưa được fit. Vui lòng gọi fit_transform trước.")
            
        cols_to_scale = [c for c in features_df.columns if not c.startswith(('hour_', 'is_', 'rsi_14_scaled'))]
        scaled_data = features_df.copy()
        
        if cols_to_scale:
            scaled_vals = self.scaler.transform(features_df[cols_to_scale])
            scaled_data[cols_to_scale] = scaled_vals
            
        return scaled_data


class LabelingV3:
    """Triple-Barrier Labeling mechanism"""
    def __init__(self, tp_pips=15, sl_pips=15, max_hold_bars=20, pip_size=0.1):
        self.tp_pips = tp_pips
        self.sl_pips = sl_pips
        self.max_hold_bars = max_hold_bars
        self.pip_size = pip_size
        
        # Convert pip to actual price unit
        self.tp_price = self.tp_pips * self.pip_size
        self.sl_price = self.sl_pips * self.pip_size

    def apply_triple_barrier(self, df, open_col, high_col, low_col):
        """
        Gắn nhãn 3-Class logic cho Bot đánh ngược/xuôi.
        Trả về Series: 0 (Sell-Win), 1 (Buy-Win), 2 (Sideway/Timeout)
        Giải thích logic chạm cản trong T tương lai:
        - Nếu chạm TP trên trước -> Market lên (Buy Win = Class 1)
        - Nếu chạm TP dưới (hoặc SL) trước -> Market xuống (Sell Win = Class 0)
        - Nếu hết nến vẫn nằm yên -> Sideway = Class 2
        """
        labels = np.full(len(df), 2, dtype=int) # Mặc định là 2 (Sideway)
        
        # Trích xuất dạng NumPy arrays để quét bằng C cho nhanh (pandas iterrows quá chậm)
        open_prices = df[open_col].values
        high_prices = df[high_col].values
        low_prices = df[low_col].values
        n_rows = len(df)
        
        for i in range(n_rows - 1):
            entry_price = open_prices[i + 1] # Vào lệnh tại nến MỞ CỬA của nến tiếp theo
            
            upper_barrier = entry_price + self.tp_price # Lệnh Buy cắn TP / Lệnh Sell cắn SL
            lower_barrier = entry_price - self.sl_price # Lệnh Buy cắn SL / Lệnh Sell cắn TP
            
            limit_idx = min(i + 1 + self.max_hold_bars, n_rows)
            
            for j in range(i + 1, limit_idx):
                h = high_prices[j]
                l = low_prices[j]
                
                # Kiểm tra nến nào cắn trên hoặc dưới trước
                hit_upper = h >= upper_barrier
                hit_lower = l <= lower_barrier
                
                if hit_upper and hit_lower:
                    # Râu nến quét 2 đầu, ưu tiên Sideway để bảo toàn vốn
                    labels[i] = 2
                    break
                elif hit_upper:
                    labels[i] = 1 # Market đâm lên -> Buy Win
                    break
                elif hit_lower:
                    labels[i] = 0 # Market đâm xuống -> Sell Win
                    break
                    
        return pd.Series(labels, index=df.index, name='target_class')
