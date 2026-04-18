import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

class FeatureEngineeringV3:
    """
    Module xử lý Feature Engineering chuẩn V3 AAMT.
    Tập trung vào tính toán 4 nhóm đặc trưng trực giao, loại bỏ nhiễu và dư thừa.
    """
    def __init__(self, target_prefix="XAUUSDm", macro_features=None, crypto_mode: bool = False):
        self.target_prefix = target_prefix
        self.macro_features = macro_features if macro_features else {}
        self.crypto_mode = crypto_mode
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
        
        # Tính tổng chiều dài cản (Spread)
        total_spread = df[high_col] - df[low_col] + 1e-6
        
        # Bóng trên tỷ lệ với tổng độ dài nến (luôn nằm trong [0, 1])
        max_oc = np.maximum(df[open_col], df[close_col])
        features['upper_wick_pct'] = (df[high_col] - max_oc) / total_spread
        
        # Bóng dưới tỷ lệ với tổng độ dài nến (luôn nằm trong [0, 1])
        min_oc = np.minimum(df[open_col], df[close_col])
        features['lower_wick_pct'] = (min_oc - df[low_col]) / total_spread
        
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
        
    def calculate_time_context(self, df, crypto_mode: bool = False):
        """
        Tính toán Ngữ cảnh thời gian.
        - Forex: Sin/Cos + One-Hot session (Asian/London/NY)
        - Crypto mode: chỉ Sin/Cos (loại bỏ session flags vì Crypto 24/7)
        """
        features = pd.DataFrame(index=df.index)
        hour = df.index.hour

        # Cyclical Time Encoding (luôn giữ)
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)

        if not crypto_mode:
            # One-Hot Encoding Phiên (chỉ dùng cho Forex/Vàng)
            features['is_asian']  = ((hour >= 0)  & (hour < 7)).astype(float)
            features['is_london'] = ((hour >= 7)  & (hour < 13)).astype(float)
            features['is_ny']     = ((hour >= 13) & (hour < 22)).astype(float)

        return features

    def process_features(self, df):
        """Hành trình nhào nặn gộp toàn bộ 4 nhánh tín hiệu"""
        # Xác định cột dựa trên target_prefix, dự phòng tên viết thường
        prefix = self.target_prefix.lower() if self.target_prefix.lower() + "_close" in map(str.lower, df.columns) else self.target_prefix
        
        # Lấy tên chính xác từ DF cho XAU
        cols = {c.lower(): c for c in df.columns}
        try:
            open_col = cols[f"{prefix}_open".lower()]
            high_col = cols[f"{prefix}_high".lower()]
            low_col = cols[f"{prefix}_low".lower()]
            close_col = cols[f"{prefix}_close".lower()]
        except KeyError as e:
            raise KeyError(f"Không tìm đủ các cột OHLC cho mã {prefix}. Chi tiết lỗi: {e}")

        # Ráp các nhánh features của Mã Chính (XAU)
        f_pa = self.calculate_price_action(df, open_col, high_col, low_col, close_col)
        f_vol = self.calculate_volatility(df, high_col, low_col, close_col)
        f_mom = self.calculate_momentum(df, close_col)
        crypto_mode = getattr(self, 'crypto_mode', False)
        f_time = self.calculate_time_context(df, crypto_mode=crypto_mode)
        
        feature_blocks = [f_pa, f_vol, f_mom, f_time]
        
        # Xử lý các mã Kinh tế Vĩ Mô (Macro)
        if self.macro_features:
            for sym, req_features in self.macro_features.items():
                sym_lower = sym.lower()
                
                # Tìm cột close và high, low của Macro
                try:
                    m_close = cols.get(f"{sym_lower}_close".lower()) or cols.get(f"{sym_lower}_usd_close".lower())
                    m_high = cols.get(f"{sym_lower}_high".lower()) or cols.get(f"{sym_lower}_usd_high".lower())
                    m_low = cols.get(f"{sym_lower}_low".lower()) or cols.get(f"{sym_lower}_usd_low".lower())
                    m_open = cols.get(f"{sym_lower}_open".lower()) or cols.get(f"{sym_lower}_usd_open".lower())
                    
                    if m_close and m_open:
                        f_macro = pd.DataFrame(index=df.index)
                        
                        if "log_ret" in req_features:
                            prev_close = df[m_close].shift(1).bfill()
                            f_macro[f"{sym}_log_ret"] = np.log((df[m_close] / prev_close) + 1e-6)
                        
                        if "bb_width" in req_features and m_high and m_low:
                            vol_macro = self.calculate_volatility(df, m_high, m_low, m_close)
                            f_macro[f"{sym}_bb_width"] = vol_macro['bb_width']
                            
                        if "volume" in req_features:
                            m_vol = cols.get(f"{sym_lower}_volume".lower()) or cols.get(f"{sym_lower}_tick_volume".lower())
                            if m_vol:
                                f_macro[f"{sym}_volume"] = df[m_vol]
                            
                        feature_blocks.append(f_macro)
                    else:
                        raise ValueError(f"FATAL ERROR: BẮT BUỘC MÃ {sym} PHẢI CÓ DỮ LIỆU ĐẦU VÀO NHƯNG KHÔNG TÌM THẤY! HỆ THỐNG TỰ HUỶ ĐỂ ĐẢM BẢO CHẤT LƯỢNG.")
                except Exception as e:
                    raise KeyError(f"FATAL ERROR: LỖI ÁNH XẠ DỮ LIỆU VĨ MÔ BẮT BUỘC CHO {sym}. Lỗi: {e}")
        
        # Nối tất cả vào chung một khung
        final_features = pd.concat(feature_blocks, axis=1)
        
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
            # Bóp trần (clip) để trị bạo loạn từ những outlier siêu khổng lồ (khi IQR quá nhỏ do Market đóng GAP)
            scaled_vals = np.clip(scaled_vals, -15.0, 15.0)
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
            scaled_vals = np.clip(scaled_vals, -15.0, 15.0)
            scaled_data[cols_to_scale] = scaled_vals
            
        return scaled_data


class LabelingV3:
    """
    Triple-Barrier Labeling mechanism.
    - Pip mode (Forex/Vàng): TP/SL tính bằng pip cố định (tp_pips * pip_size)
    - Pct mode (Crypto):     TP/SL tính theo % của giá vào lệnh (tp_pct, sl_pct)
    """
    def __init__(self, tp_pips=10, sl_pips=10, max_hold_bars=15, pip_size=0.1,
                 label_mode='pip', tp_pct=0.003, sl_pct=0.003):
        self.max_hold_bars = max_hold_bars
        self.label_mode = label_mode  # 'pip' hoặc 'pct'

        # Pip mode params
        self.tp_pips  = tp_pips
        self.sl_pips  = sl_pips
        self.pip_size = pip_size
        self.tp_price = tp_pips * pip_size
        self.sl_price = sl_pips * pip_size

        # Pct mode params (dùng cho Crypto)
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct

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
        
        use_pct = (self.label_mode == 'pct')

        for i in range(n_rows - 1):
            entry_price = open_prices[i + 1]  # Vào lệnh tại nến MỞ CỬA của nến tiếp theo

            if use_pct:
                # % mode: TP/SL là tỷ lệ phần trăm của giá vào lệnh — bền vững với mọi mức giá
                upper_barrier = entry_price * (1.0 + self.tp_pct)
                lower_barrier = entry_price * (1.0 - self.sl_pct)
            else:
                # Pip mode: TP/SL là khoảng giá cố định (pips * pip_size)
                upper_barrier = entry_price + self.tp_price
                lower_barrier = entry_price - self.sl_price

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
