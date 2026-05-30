import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler

class FeatureEngineeringV3:
    """
    Module xử lý Feature Engineering chuẩn V3 AAMT.
    Tập trung vào tính toán 4 nhóm đặc trưng trực giao, loại bỏ nhiễu và dư thừa.
    
    [V2] Tùy chọn nâng cao (backward-compatible):
    - mtf_windows: Multi-Timeframe log_return & ATR trên cửa sổ lớn hơn
    - order_flow:  Delta Volume + Cumulative Delta proxy
    - vol_regime:  Phân loại chế độ biến động High/Med/Low (one-hot)
    """
    def __init__(self, target_prefix="XAUUSDm", macro_features=None, crypto_mode: bool = False,
                 mtf_windows=None, order_flow: bool = False, vol_regime: bool = False,
                 zero_noise_target: bool = False, indicators_cfg=None):
        self.target_prefix = target_prefix
        self.macro_features = macro_features if macro_features else {}
        self.crypto_mode = crypto_mode
        self.mtf_windows = mtf_windows or []  # e.g. [5, 15, 60]
        self.order_flow = order_flow
        self.vol_regime = vol_regime
        self.zero_noise_target = zero_noise_target
        self.indicators_cfg = indicators_cfg or {}
        self.scaler = RobustScaler()
        self.is_fitted = False
        
    def calculate_price_action(self, df, open_col, high_col, low_col, close_col):
        """Tính toán nhóm Hình thái giá: Log Returns và Bóng nến"""
        features = pd.DataFrame(index=df.index)
        
        # Log Returns (so với giá đóng cửa phiên trước để giữ tính liên tục)
        prev_close = df[close_col].shift(1)
        # Điền NaN đầu tiên bằng chính giá open của nến đó để tránh rách index
        prev_close = prev_close.bfill()
        
        # Cộng thêm epsilon nhỏ (1e-6) để tránh log(0)
        features['log_return_open']  = np.log((df[open_col]  / prev_close) + 1e-6)
        features['log_return_high']  = np.log((df[high_col]  / prev_close) + 1e-6)
        features['log_return_low']   = np.log((df[low_col]   / prev_close) + 1e-6)
        features['log_return_close'] = np.log((df[close_col] / prev_close) + 1e-6)
        
        # Tổng chiều dài cản (Spread)
        total_spread = df[high_col] - df[low_col] + 1e-6
        
        # Bóng trên tỷ lệ với tổng độ dài nến (luôn nằm trong [0, 1])
        max_oc = np.maximum(df[open_col], df[close_col])
        features['upper_wick_pct'] = (df[high_col] - max_oc) / total_spread
        
        # Bóng dưới tỷ lệ với tổng độ dài nến (luôn nằm trong [0, 1])
        min_oc = np.minimum(df[open_col], df[close_col])
        features['lower_wick_pct'] = (min_oc - df[low_col]) / total_spread
        
        return features
        
    def calculate_microstructure(self, df, open_col, high_col, low_col, close_col,
                                  volume_col=None, adx_period=None, vwap_period=None, taker_buy_col=None, taker_sell_col=None):
        """
        [MỚI - P1/P2] Nhóm Vi cấu trúc thị trường:
        - body_pct   : Độ đặc của thân nến (Marubozu detection)
        - vroc       : Relative Volume (Volume / SMA20-Volume)
        - adx_norm   : Sức mạnh xu hướng ADX, chuẩn hóa [0, 1]
        - vwap_dist  : Khoảng cách giữa Close và VWAP xấp xỉ (Mean Reversion signal)
        """
        adx_period = adx_period or self.indicators_cfg.get("ADX_PERIOD", 10)
        vwap_period = vwap_period or self.indicators_cfg.get("VWAP_PERIOD", 20)
        sma_vol_period = self.indicators_cfg.get("SMA_VOL_PERIOD", 60)
        features = pd.DataFrame(index=df.index)
        total_spread = df[high_col] - df[low_col] + 1e-6
        
        # -- body_pct: Tỷ lệ thân nến trong khoảng [0, 1]
        body = (df[close_col] - df[open_col]).abs()
        features['body_pct'] = body / total_spread
        
        if volume_col and volume_col in df.columns:
            vol = df[volume_col].clip(lower=0)  # loại volume âm nếu lỗi adapter
            
            # -- vroc: Relative Volume so với SMA-20
            sma_vol = vol.rolling(window=20, min_periods=1).mean()
            features['vroc'] = vol / (sma_vol + 1e-6)
            
            # -- vwap_distance: Anchored Daily VWAP (reset 00:00 UTC mỗi ngày)
            # Đúng định nghĩa Quant: cộng dồn lũy kế từ 00:00 UTC, reset hàng ngày
            typical = (df[high_col] + df[low_col] + df[close_col]) / 3.0
            pv = typical * vol
            day_key = df.index.normalize()  # tz-aware date key (00:00 UTC)
            cum_pv  = pv.groupby(day_key).cumsum()
            cum_vol = vol.groupby(day_key).cumsum()
            vwap = cum_pv / (cum_vol + 1e-6)
            features['vwap_distance'] = (df[close_col] - vwap) / (vwap + 1e-6)
            
            # -- [MỚI V4] NY Anchored VWAP (reset lúc 13:30 UTC)
            ny_open_mask = (df.index.hour == 13) & (df.index.minute == 30)
            ny_session_key = ny_open_mask.cumsum()
            cum_pv_ny = pv.groupby(ny_session_key).cumsum()
            cum_vol_ny = vol.groupby(ny_session_key).cumsum()
            vwap_ny = cum_pv_ny / (cum_vol_ny + 1e-6)
            features['vwap_distance_ny'] = (df[close_col] - vwap_ny) / (vwap_ny + 1e-6)

            # -- [MỚI V4] Order Flow Imbalance (Taker Buy vs Taker Sell)
            if taker_buy_col and taker_sell_col and taker_buy_col in df.columns and taker_sell_col in df.columns:
                taker_buy = df[taker_buy_col].clip(lower=0)
                taker_sell = df[taker_sell_col].clip(lower=0)
                features['order_flow_imbalance'] = (taker_buy - taker_sell) / (vol + 1e-6)
                # Tích luỹ Order Flow Imbalance trong phiên NY (từ 13:30 UTC)
                features['cum_ofi_ny'] = features['order_flow_imbalance'].groupby(ny_session_key).cumsum()
            
            # -- [MỚI V4] Funding Rate
            if 'fundingRate' in df.columns:
                features['funding_rate'] = df['fundingRate']
                features['funding_rate_change'] = df['fundingRate'] - df['fundingRate'].shift(1).bfill()

            # -- [MỚI - NY Session] Daily High / Low Liquidity Magnets
            daily_high = df[high_col].groupby(day_key).cummax()
            daily_low = df[low_col].groupby(day_key).cummin()
            features['dist_to_daily_high'] = (daily_high - df[close_col]) / (df[close_col] + 1e-6)
            features['dist_to_daily_low'] = (df[close_col] - daily_low) / (daily_low + 1e-6)
            
            # -- [MỚI - London Session] Asian Session Liquidity Magnets
            asian_mask = df.index.hour < 7
            asian_highs = df[high_col].where(asian_mask).groupby(day_key).cummax().groupby(day_key).ffill()
            asian_lows = df[low_col].where(asian_mask).groupby(day_key).cummin().groupby(day_key).ffill()
            features['asian_high_dist'] = ((asian_highs - df[close_col]) / (df[close_col] + 1e-6)).fillna(0.0)
            features['asian_low_dist'] = ((df[close_col] - asian_lows) / (asian_lows + 1e-6)).fillna(0.0)
            
            # -- [MỚI - NY Session] London Session Liquidity Magnets (07:00 - 13:00)
            london_mask = (df.index.hour >= 7) & (df.index.hour < 13)
            london_highs = df[high_col].where(london_mask).groupby(day_key).cummax().groupby(day_key).ffill()
            london_lows = df[low_col].where(london_mask).groupby(day_key).cummin().groupby(day_key).ffill()
            features['london_high_dist'] = ((london_highs - df[close_col]) / (df[close_col] + 1e-6)).fillna(0.0)
            features['london_low_dist'] = ((df[close_col] - london_lows) / (london_lows + 1e-6)).fillna(0.0)

            # -- [MỚI - Close Session] NY Session Liquidity Magnets (13:00 - 22:00)
            ny_mask = (df.index.hour >= 13) & (df.index.hour < 22)
            ny_highs = df[high_col].where(ny_mask).groupby(day_key).cummax().groupby(day_key).ffill()
            ny_lows = df[low_col].where(ny_mask).groupby(day_key).cummin().groupby(day_key).ffill()
            features['ny_high_dist'] = ((ny_highs - df[close_col]) / (df[close_col] + 1e-6)).fillna(0.0)
            features['ny_low_dist'] = ((df[close_col] - ny_lows) / (ny_lows + 1e-6)).fillna(0.0)
            
            # -- [MỚI - London Session] Volume Surge Ratio
            sma_vol_60 = vol.rolling(window=sma_vol_period, min_periods=1).mean()
            features['vol_surge_ratio'] = vol / (sma_vol_60 + 1e-6)
            
            # -- [MỚI - NY Session] Exhaustion & Acceleration
            features['vol_accel'] = vol - vol.shift(1).bfill()
            
            is_green = (df[close_col] > df[open_col]).astype(int)
            is_red = (df[close_col] < df[open_col]).astype(int)
            sign = is_green - is_red
            streak_groups = (sign != sign.shift()).cumsum()
            features['streak_count'] = sign.groupby(streak_groups).cumsum()
            
            upper_wick = df[high_col] - np.maximum(df[open_col], df[close_col])
            lower_wick = np.minimum(df[open_col], df[close_col]) - df[low_col]
            total_wick = upper_wick + lower_wick
            features['wick_accel'] = total_wick - total_wick.shift(1).bfill()
            
            # -- [MỚI - SA Review #5] VSA: Effort vs Result (Nỗ lực vs Kết quả)
            # Khối lượng lớn nhưng biến động giá thấp -> Dấu hiệu hấp thụ (Absorption), chặn đảo chiều
            # Dùng np.log1p để tránh hiện tượng phương sai nổ khổng lồ khi spread cực nhỏ (nến Doji)
            candle_length = df[high_col] - df[low_col]
            features['volume_effort'] = np.log1p(vol / (candle_length + 1e-6))
        
        # -- adx_normalized: ADX(period) chuẩn hóa về [0, 1]
        high  = df[high_col]
        low   = df[low_col]
        prev_close = df[close_col].shift(1).bfill()
        
        plus_dm  = (high.diff()).clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)
        # Chỉ giữ DM lớn hơn, set nhỏ hơn = 0
        cond = plus_dm >= minus_dm
        plus_dm_clean  = plus_dm.where(cond, 0.0)
        minus_dm_clean = minus_dm.where(~cond, 0.0)
        
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': (high - prev_close).abs(),
            'lc': (low  - prev_close).abs()
        }).max(axis=1)
        
        smoothed_tr   = tr.ewm(span=adx_period, adjust=False).mean()
        plus_di  = 100 * plus_dm_clean.ewm(span=adx_period,  adjust=False).mean() / (smoothed_tr + 1e-6)
        minus_di = 100 * minus_dm_clean.ewm(span=adx_period, adjust=False).mean() / (smoothed_tr + 1e-6)
        dx  = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6)
        adx = dx.ewm(span=adx_period, adjust=False).mean()
        features['adx_normalized'] = adx / 100.0  # [0, 1]
        
        return features

    # =====================================================================
    # [MỚI] Multi-Timeframe Features — Nhìn bức tranh lớn từ M1
    # =====================================================================
    def calculate_multi_timeframe(self, df, close_col, high_col, low_col):
        """
        Tính log_return và ATR trên các cửa sổ lớn hơn (vd: 5, 15, 60 nến).
        Cho phép model "zoom out" mà không cần thay đổi WINDOW_SIZE của input tensor.
        """
        features = pd.DataFrame(index=df.index)
        for w in self.mtf_windows:
            # Multi-timeframe log return
            features[f'mtf_ret_{w}'] = np.log((df[close_col] / df[close_col].shift(w).bfill()) + 1e-6)
            # Multi-timeframe ATR ratio (ATR_w / ATR_14)
            prev_close = df[close_col].shift(1).bfill()
            tr = pd.DataFrame({
                'hl': df[high_col] - df[low_col],
                'hc': (df[high_col] - prev_close).abs(),
                'lc': (df[low_col] - prev_close).abs()
            }).max(axis=1)
            atr_w = tr.rolling(window=w, min_periods=1).mean()
            atr_period = self.indicators_cfg.get("ATR_PERIOD", 14)
            atr_14 = tr.rolling(window=atr_period, min_periods=1).mean()
            features[f'mtf_atr_ratio_{w}'] = atr_w / (atr_14 + 1e-6)
        return features

    # =====================================================================
    # [MỚI] Order Flow Proxy — Xấp xỉ Volume Delta từ M1 OHLCV
    # =====================================================================
    def calculate_order_flow(self, df, open_col, close_col, volume_col):
        """
        Tính delta_volume (volume × direction) và cumulative delta trong phiên.
        Giúp AI nhận diện vùng hấp thụ (absorption) và áp lực mua/bán.
        """
        features = pd.DataFrame(index=df.index)
        if not volume_col or volume_col not in df.columns:
            return features
        vol = df[volume_col].clip(lower=0)
        direction = np.sign(df[close_col] - df[open_col])
        features['delta_volume'] = vol * direction
        # Cumulative delta reset hàng ngày
        day_key = df.index.normalize()
        features['cum_delta_session'] = features['delta_volume'].groupby(day_key).cumsum()
        return features

    # =====================================================================
    # [MỚI] Volatility Regime — Phân loại chế độ biến động
    # =====================================================================
    def calculate_vol_regime(self, df, high_col, low_col, close_col):
        """
        Dùng ATR percentile 20 nến để one-hot encode 3 chế độ:
        - Low vol (ATR < P33)
        - Medium vol (P33 <= ATR < P66)  
        - High vol (ATR >= P66)
        """
        features = pd.DataFrame(index=df.index)
        vol_regime_window = self.indicators_cfg.get("VOL_REGIME_WINDOW", 200)
        atr_period = self.indicators_cfg.get("ATR_PERIOD", 20)
        prev_close = df[close_col].shift(1).bfill()
        tr = pd.DataFrame({
            'hl': df[high_col] - df[low_col],
            'hc': (df[high_col] - prev_close).abs(),
            'lc': (df[low_col] - prev_close).abs()
        }).max(axis=1)
        atr_20 = tr.rolling(window=atr_period, min_periods=1).mean()
        p33 = atr_20.rolling(window=vol_regime_window, min_periods=20).quantile(0.33)
        p66 = atr_20.rolling(window=vol_regime_window, min_periods=20).quantile(0.66)
        features['vol_regime_low'] = (atr_20 < p33).astype(float)
        features['vol_regime_high'] = (atr_20 >= p66).astype(float)
        return features

        
    def calculate_volatility(self, df, high_col, low_col, close_col, bb_period=None, atr_period=None):
        """Tính toán nhóm Biến động: ATR chuẩn hóa và Bollinger Band Width"""
        features = pd.DataFrame(index=df.index)
        bb_period = bb_period or self.indicators_cfg.get("BB_PERIOD", 20)
        atr_period = atr_period or self.indicators_cfg.get("ATR_PERIOD", 14)
        
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
        features['bb_zscore'] = (df[close_col] - sma) / (rstd + 1e-6)
        
        # [MỚI - NY Session] Choppiness Index (CHOP_14)
        sum_atr = atr.rolling(window=atr_period, min_periods=1).sum()
        max_high = df[high_col].rolling(window=atr_period, min_periods=1).max()
        min_low = df[low_col].rolling(window=atr_period, min_periods=1).min()
        chop = 100 * np.log10(sum_atr / (max_high - min_low + 1e-6) + 1e-6) / np.log10(atr_period)
        features[f'chop_{atr_period}'] = chop / 100.0  # normalize to [0,1]
        
        return features
        
    def calculate_momentum(self, df, close_col, rsi_period=None, macd_fast=None, macd_slow=None, macd_signal=None):
        """Tính toán nhóm Động lượng: RSI và MACD Histogram"""
        features = pd.DataFrame(index=df.index)
        rsi_period = rsi_period or self.indicators_cfg.get("RSI_PERIOD", 14)
        rsi_fast = self.indicators_cfg.get("RSI_FAST", 5)
        macd_fast = macd_fast or self.indicators_cfg.get("MACD_FAST", 12)
        macd_slow = macd_slow or self.indicators_cfg.get("MACD_SLOW", 26)
        macd_signal = macd_signal or self.indicators_cfg.get("MACD_SIGNAL", 9)
        
        # Tính RSI
        delta = df[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period, min_periods=1).mean()
        
        rs = gain / (loss + 1e-6)
        rsi = 100 - (100 / (1 + rs))
        # Chuẩn hóa RSI về [-1, 1] cho Neural Network dễ học
        features[f'rsi_{rsi_period}_scaled'] = (rsi / 50.0) - 1.0
        
        # Thêm RSI siêu ngắn (RSI 5) để bắt Mean Reversion độ trễ thấp
        gain_5 = (delta.where(delta > 0, 0)).rolling(window=rsi_fast, min_periods=1).mean()
        loss_5 = (-delta.where(delta < 0, 0)).rolling(window=rsi_fast, min_periods=1).mean()
        rs_5 = gain_5 / (loss_5 + 1e-6)
        rsi_5 = 100 - (100 / (1 + rs_5))
        features[f'rsi_{rsi_fast}_scaled'] = (rsi_5 / 50.0) - 1.0
        
        # Tính MACD
        ema_fast = df[close_col].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = df[close_col].ewm(span=macd_slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=macd_signal, adjust=False).mean()
        macd_hist = macd_line - signal_line
        
        # Dùng trực tiếp giá trị MACD Histogram vì nó đã dao động quanh 0, bước RobustScaler sẽ co giãn lại
        features['macd_hist'] = macd_hist
        
        return features
        
    def calculate_time_context(self, df, crypto_mode: bool = False, open_col=None, close_col=None):
        """
        Tính toán Ngữ cảnh thời gian.
        - Forex: Sin/Cos + One-Hot session (Asian/London/NY) + Session Open Distances
        - Crypto mode: chỉ Sin/Cos (loại bỏ session flags vì Crypto 24/7)
        """
        features = pd.DataFrame(index=df.index)
        hour = df.index.hour
        minute = df.index.minute

        # Cyclical Time Encoding (luôn giữ)
        features['hour_sin'] = np.sin(2 * np.pi * hour / 24.0)
        features['hour_cos'] = np.cos(2 * np.pi * hour / 24.0)
        features['minute_sin'] = np.sin(2 * np.pi * minute / 60.0)
        features['minute_cos'] = np.cos(2 * np.pi * minute / 60.0)

        if not crypto_mode:
            # One-Hot Encoding Phiên (chỉ dùng cho Forex/Vàng)
            features['is_asian']  = ((hour >= 0)  & (hour < 7)).astype(float)
            features['is_london'] = ((hour >= 7)  & (hour < 13)).astype(float)
            features['is_ny']     = ((hour >= 13) & (hour < 22)).astype(float)
            
            # [MỚI - SA Review #5] Cờ Giao Thoa London - NY (12:00 - 13:00 UTC)
            # Nợ kỹ thuật (Q2/2026): Cần check lịch DST chuẩn xác vì lệch tuần. Tạm tính là 12h.
            features['is_overlap'] = (hour == 12).astype(float)
            
            # [MỚI - NY Session] Quan trọng: Cờ giờ mở cửa cổ phiếu
            features['is_nyse_open'] = ((hour == 13) & (minute >= 30)).astype(float)
            features['is_london_fix'] = ((hour == 15) & (minute >= 30)).astype(float)
            
            # [MỚI - SA Review #4] Khoảng cách đến New York/London/Asian Open
            if open_col and close_col:
                # London (07:00 UTC)
                london_mask = (hour == 7) & (minute == 0)
                london_open_px = df[open_col].where(london_mask).ffill()
                features['london_open_dist'] = ((df[close_col] - london_open_px) / (london_open_px + 1e-6)).fillna(0.0)
                
                # Asian (00:00 UTC)
                asian_mask = (hour == 0) & (minute == 0)
                asian_open_px = df[open_col].where(asian_mask).ffill()
                features['asian_open_dist'] = ((df[close_col] - asian_open_px) / (asian_open_px + 1e-6)).fillna(0.0)
                
                # NY (13:00 UTC)
                ny_mask = (hour == 13) & (minute == 0)
                ny_open_px = df[open_col].where(ny_mask).ffill()
                features['ny_open_dist'] = ((df[close_col] - ny_open_px) / (ny_open_px + 1e-6)).fillna(0.0)

        return features

    def process_features(self, df):
        """Hành trình nhào nặn gộp toàn bộ 4 nhánh tín hiệu"""
        rsi_period = self.indicators_cfg.get("RSI_PERIOD", 14)
        rsi_fast = self.indicators_cfg.get("RSI_FAST", 5)
        atr_period = self.indicators_cfg.get("ATR_PERIOD", 14)
        # Xác định cột dựa trên target_prefix, dự phòng tên viết thường
        prefix = self.target_prefix.lower() if self.target_prefix.lower() + "_close" in map(str.lower, df.columns) else self.target_prefix
        
        # Lấy tên chính xác từ DF cho XAU
        cols = {c.lower(): c for c in df.columns}
        print(f"[DEBUG FE] target_prefix={self.target_prefix}, cols={list(cols.keys())}")
        try:
            open_col = cols[f"{prefix}_open".lower()]
            high_col = cols[f"{prefix}_high".lower()]
            low_col = cols[f"{prefix}_low".lower()]
            close_col = cols[f"{prefix}_close".lower()]
        except KeyError as e:
            raise KeyError(f"Không tìm đủ các cột OHLC cho mã {prefix}. Chi tiết lỗi: {e}")

        # Ráp các nhánh features của Mã Chính
        f_pa = self.calculate_price_action(df, open_col, high_col, low_col, close_col)
        f_vol = self.calculate_volatility(df, high_col, low_col, close_col)
        f_mom = self.calculate_momentum(df, close_col)
        crypto_mode = getattr(self, 'crypto_mode', False)
        f_time = self.calculate_time_context(df, crypto_mode=crypto_mode, open_col=open_col, close_col=close_col)
        
        # [MỚI P1/P2] Microstructure features: body_pct, vroc, adx, vwap_distance
        volume_col = cols.get(f"{prefix}_volume".lower()) or cols.get(f"{prefix}_real_volume".lower())
        taker_buy_col = cols.get(f"{prefix}_taker_buy_volume".lower()) or cols.get("taker_buy_volume")
        taker_sell_col = cols.get(f"{prefix}_taker_sell_volume".lower()) or cols.get("taker_sell_volume")
        f_micro = self.calculate_microstructure(df, open_col, high_col, low_col, close_col, volume_col=volume_col, taker_buy_col=taker_buy_col, taker_sell_col=taker_sell_col)
        
        if getattr(self, 'zero_noise_target', False):
            print("[FE] CẢNH BÁO: Kích hoạt ZERO_NOISE_TARGET! Loại bỏ toàn bộ TA rác của Target Symbol (chỉ giữ log_ret, spread, volume, time).")
            # Chỉ giữ log_ret từ f_pa
            f_pa = f_pa[['log_ret']] if 'log_ret' in f_pa.columns else pd.DataFrame(index=df.index)
            # Giữ lại bb_width và atr_normalized nếu có, không giữ chop_14, bb_zscore
            cols_to_keep = [c for c in f_vol.columns if c in ['atr_normalized', 'bb_width']]
            f_vol = f_vol[cols_to_keep]
            # Loại bỏ hoàn toàn f_mom, f_micro
            feature_blocks = [f_pa, f_vol, f_time]
            
            # Thêm thủ công volume và spread (nếu có) vào f_micro tạm thời để không bị rỗng
            f_micro_clean = pd.DataFrame(index=df.index)
            if volume_col and volume_col in df.columns:
                f_micro_clean['volume'] = np.log1p(df[volume_col].clip(lower=0).fillna(0))
            else:
                f_micro_clean['volume'] = 0.0 # Fallback
                
            spread_col = cols.get(f"{prefix}_spread".lower())
            if spread_col and spread_col in df.columns:
                f_micro_clean['spread'] = np.log1p(df[spread_col].clip(lower=0).fillna(0))
            else:
                f_micro_clean['spread'] = 0.0 # Fallback for Binance/Crypto
                
            if 'order_flow_imbalance' in f_micro.columns:
                f_micro_clean['order_flow_imbalance'] = f_micro['order_flow_imbalance']
                
            if not f_micro_clean.empty:
                feature_blocks.append(f_micro_clean)
        else:
            feature_blocks = [f_pa, f_vol, f_mom, f_time, f_micro]
        
        # [MỚI V2] Multi-Timeframe Features
        if self.mtf_windows:
            f_mtf = self.calculate_multi_timeframe(df, close_col, high_col, low_col)
            feature_blocks.append(f_mtf)
            print(f"[FE] Multi-Timeframe features added: windows={self.mtf_windows}, cols={list(f_mtf.columns)}")
        
        # [MỚI V2] Order Flow Proxy
        if self.order_flow:
            f_of = self.calculate_order_flow(df, open_col, close_col, volume_col)
            if not f_of.empty:
                feature_blocks.append(f_of)
                print(f"[FE] Order Flow features added: {list(f_of.columns)}")
        
        # [MỚI V2] Volatility Regime
        if self.vol_regime:
            f_vr = self.calculate_vol_regime(df, high_col, low_col, close_col)
            feature_blocks.append(f_vr)
            print(f"[FE] Volatility Regime features added: {list(f_vr.columns)}")
        
        # Xử lý các mã Kinh tế Vĩ Mô (Macro)
        if self.macro_features:
            for sym, req_features in self.macro_features.items():
                sym_lower = sym.lower()
                
                # Tìm cột close và high, low của Macro
                try:
                    sym_clean = sym_lower.removesuffix('m')
                    print(f"DEBUG: sym={sym}, sym_lower={sym_lower}, cols keys matching: {[k for k in cols.keys() if sym_lower in k]}")

                    
                    m_close = cols.get(f"{sym_lower}_close".lower()) or cols.get(f"{sym_lower}_usd_close".lower()) or cols.get(f"{sym_clean}_close".lower())
                    m_high = cols.get(f"{sym_lower}_high".lower()) or cols.get(f"{sym_lower}_usd_high".lower()) or cols.get(f"{sym_clean}_high".lower())
                    m_low = cols.get(f"{sym_lower}_low".lower()) or cols.get(f"{sym_lower}_usd_low".lower()) or cols.get(f"{sym_clean}_low".lower())
                    m_open = cols.get(f"{sym_lower}_open".lower()) or cols.get(f"{sym_lower}_usd_open".lower()) or cols.get(f"{sym_clean}_open".lower())
                    
                    print(f'sym={sym}, m_close={m_close}, m_open={m_open}')
                    if m_close and m_open:
                        f_macro = pd.DataFrame(index=df.index)
                        
                        if "log_ret" in req_features:
                            prev_macro_close = df[m_close].shift(1).bfill()
                            macro_ret = np.log((df[m_close] / prev_macro_close) + 1e-6)
                            f_macro[f"{sym}_log_ret"] = macro_ret
                            
                            # [FIX #1 SA] Dynamic Correlation: tính tương quan động theo config
                            # Không hardcode symbol mà dùng 'corr_60' trong req_features để bật
                            if "corr_60" in req_features:
                                target_ret = np.log(
                                    (df[close_col] / df[close_col].shift(1).bfill()) + 1e-6
                                )
                                corr = target_ret.rolling(window=60, min_periods=20).corr(macro_ret)
                                f_macro[f"{sym}_target_corr_60"] = corr.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-1.0, 1.0)
                            
                            # [MỚI - NY Session] Macro Divergence: DXY_XAU Anomaly
                            if sym_lower.startswith('dxy'):
                                target_ret = np.log((df[close_col] / df[close_col].shift(1).bfill()) + 1e-6)
                                f_macro[f"{sym}_dxy_xau_anomaly"] = macro_ret * target_ret
                            
                            # [MỚI V2] Cross-Asset Spread Return
                            if "spread_ret" in req_features:
                                target_ret = np.log((df[close_col] / df[close_col].shift(1).bfill()) + 1e-6)
                                f_macro[f"{sym}_spread_ret"] = target_ret - macro_ret
                            
                            # [MỚI V2] Relative Strength (rolling cumulative return ratio)
                            if "relative_strength" in req_features:
                                target_cum = np.log((df[close_col] / df[close_col].shift(1).bfill()) + 1e-6).rolling(window=60, min_periods=5).sum()
                                macro_cum = macro_ret.rolling(window=60, min_periods=5).sum()
                                f_macro[f"{sym}_relative_strength"] = (target_cum - macro_cum).fillna(0.0)
                        
                        if any(f in req_features for f in ["bb_width", "bb_zscore", "chop_14"]) and m_high and m_low:
                            vol_macro = self.calculate_volatility(df, m_high, m_low, m_close)
                            if "bb_width" in req_features:
                                f_macro[f"{sym}_bb_width"] = vol_macro['bb_width']
                            if "bb_zscore" in req_features:
                                f_macro[f"{sym}_bb_zscore"] = vol_macro['bb_zscore']
                            if "chop_14" in req_features:
                                f_macro[f"{sym}_chop_14"] = vol_macro[f'chop_{atr_period}']

                        # [MỚI V5] Thêm Momentum cho Macro
                        if any(f in req_features for f in ["rsi_14", "rsi_5", "macd_hist", "momentum_10"]) and m_close:
                            mom_macro = self.calculate_momentum(df, m_close)
                            if "rsi_14" in req_features:
                                f_macro[f"{sym}_rsi_14"] = mom_macro[f'rsi_{rsi_period}_scaled']
                            if "rsi_5" in req_features:
                                f_macro[f"{sym}_rsi_5"] = mom_macro[f'rsi_{rsi_fast}_scaled']
                            if "macd_hist" in req_features:
                                f_macro[f"{sym}_macd_hist"] = mom_macro['macd_hist']
                            if "momentum_10" in req_features:
                                # Tính momentum đơn giản: log ret 10 nến
                                f_macro[f"{sym}_momentum_10"] = np.log((df[m_close] / df[m_close].shift(10).bfill()) + 1e-6)
                            
                        if "volume" in req_features:
                            m_vol = cols.get(f"{sym_lower}_volume".lower()) or cols.get(f"{sym_lower}_tick_volume".lower()) or cols.get(f"{sym_clean}_volume".lower()) or cols.get(f"{sym_clean}_tick_volume".lower())
                            if m_vol:
                                f_macro[f"{sym}_volume"] = df[m_vol]
                                
                        if "rsi_14" in req_features:
                            delta = df[m_close].diff()
                            gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
                            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                            rs = gain / (loss + 1e-6)
                            rsi = 100 - (100 / (1 + rs))
                            f_macro[f"{sym}_rsi_14"] = (rsi / 50.0) - 1.0
                            
                        if "momentum_10" in req_features:
                            f_macro[f"{sym}_momentum_10"] = df[m_close].diff(10).fillna(0.0)
                            
                        feature_blocks.append(f_macro)
                    else:
                        raise ValueError(f"FATAL ERROR: BẮT BUỘC MÃ {sym} PHẢI CÓ DỮ LIỆU ĐẦU VÀO NHƯNG KHÔNG TÌM THẤY! HỆ THỐNG TỰ HUỶ ĐỂ ĐẢM BẢO CHẤT LƯỢNG.")
                except Exception as e:
                    raise KeyError(f"FATAL ERROR: LỖI ÁNH XẠ DỮ LIỆU VĨ MÔ BẮT BUỘC CHO {sym}. Lỗi: {e}")
        
        # Nối tất cả vào chung một khung
        final_features = pd.concat(feature_blocks, axis=1)
        
        # Xoá các giá trị NaN phát sinh do độ trễ rolling window
        # final_features = final_features.bfill() # FIXED: DO NOT bfill, keep NaNs to drop later
        
        return final_features
        
    def fit_scaler(self, features_df):
        """Chỉ tìm và lưu thông số Scaler (Median, IQR) từ dữ liệu truyền vào (thường là Train Set)"""
        rsi_period = self.indicators_cfg.get("RSI_PERIOD", 14)
        rsi_fast = self.indicators_cfg.get("RSI_FAST", 5)
        atr_period = self.indicators_cfg.get("ATR_PERIOD", 14)
        def _no_scale(col):
            return (
                col.startswith(('hour_', 'minute_', 'is_', f'rsi_{rsi_period}_scaled', f'rsi_{rsi_fast}_scaled'))
                or col in ('body_pct', 'adx_normalized', f'chop_{atr_period}', 'streak_count', 'order_flow_imbalance')
                or col.endswith('_target_corr_60')
            )
        cols_to_scale = [c for c in features_df.columns if not _no_scale(c)]
        if cols_to_scale:
            self.scaler.fit(features_df[cols_to_scale])
            self.is_fitted = True
            
    def fit_transform_scaler(self, features_df):
        """Scale data trong lúc Training"""
        rsi_period = self.indicators_cfg.get("RSI_PERIOD", 14)
        rsi_fast = self.indicators_cfg.get("RSI_FAST", 5)
        atr_period = self.indicators_cfg.get("ATR_PERIOD", 14)
        # Tránh scale các cột đã nằm trong biên [-1, 1] hoặc [0, 1]:
        # - hour_ / minute_ / is_*: Time Context
        # - rsi_*_scaled: đã chuẩn hóa thủ công về [-1, 1]
        # - body_pct, adx_normalized: luôn [0, 1]
        # - *_target_corr_60: Pearson correlation đã in [-1, 1] — dùng suffix match để bắt mọi symbol
        def _no_scale(col):
            return (
                col.startswith(('hour_', 'minute_', 'is_', f'rsi_{rsi_period}_scaled', f'rsi_{rsi_fast}_scaled'))
                or col in ('body_pct', 'adx_normalized', f'chop_{atr_period}', 'streak_count', 'order_flow_imbalance')
                or col.endswith('_target_corr_60')
            )
        cols_to_scale = [c for c in features_df.columns if not _no_scale(c)]
        
        scaled_data = features_df.copy()
        
        if cols_to_scale:
            scaled_vals = self.scaler.fit_transform(features_df[cols_to_scale])
            # Bóp trần (clip) để trị bạo loạn từ những outlier siêu khổng lồ (khi IQR quá nhỏ do Market đóng GAP)
            scaled_vals = np.clip(scaled_vals, -15.0, 15.0)
            scaled_data[cols_to_scale] = scaled_vals
            self.is_fitted = True
            
        return scaled_data
        
    def transform_scaler(self, features_df):
        """Scale data trong lúc Live Inference — trả lại TẤT CẢ cột (cả scaled lẫn passthrough)."""
        rsi_period = self.indicators_cfg.get("RSI_PERIOD", 14)
        rsi_fast = self.indicators_cfg.get("RSI_FAST", 5)
        atr_period = self.indicators_cfg.get("ATR_PERIOD", 14)
        if not self.is_fitted:
            raise ValueError("Scaler chưa được fit. Vui lòng gọi fit_transform trước.")
        
        def _no_scale(col):
            return (
                col.startswith(('hour_', 'minute_', 'is_', f'rsi_{rsi_period}_scaled', f'rsi_{rsi_fast}_scaled'))
                or col in ('body_pct', 'adx_normalized', f'chop_{atr_period}', 'streak_count', 'order_flow_imbalance')
                or col.endswith('_target_corr_60')
            )
        cols_to_scale = [c for c in features_df.columns if not _no_scale(c)]
        scaled_data = features_df.copy()
        
        if cols_to_scale:
            # Chỉ scale những cột mà scaler đã được fit (fix lỗi Feature unseen at fit time)
            # [VÁ LỖI] Bắt buộc phải giữ đúng thứ tự cột như lúc fit
            valid_cols = [c for c in self.scaler.feature_names_in_ if c in cols_to_scale]
            if valid_cols:
                scaled_vals = self.scaler.transform(features_df[valid_cols])
                scaled_vals = np.clip(scaled_vals, -15.0, 15.0)
                scaled_data[valid_cols] = scaled_vals
            
        return scaled_data


class LabelingV3:
    """
    Triple-Barrier Labeling mechanism.
    - Pip mode (Forex/Vàng): TP/SL tính bằng pip cố định (tp_pips * pip_size)
    - Pct mode (Crypto):     TP/SL tính theo % của giá vào lệnh (tp_pct, sl_pct)
    """
    def __init__(self, tp_pips=10, sl_pips=10, max_hold_bars=15, pip_size=0.1,
                 label_mode='pip', tp_pct=0.003, sl_pct=0.003,
                 spread_pips=0.0, spread_pct=0.0):
        self.max_hold_bars = max_hold_bars
        self.label_mode = label_mode  # 'pip' hoặc 'pct'

        # Pip mode params
        self.tp_pips  = tp_pips
        self.sl_pips  = sl_pips
        self.pip_size = pip_size
        self.tp_price = tp_pips * pip_size
        self.sl_price = sl_pips * pip_size
        self.spread_price = spread_pips * pip_size

        # Pct mode params (dùng cho Crypto)
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.spread_pct = spread_pct

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
                # % mode: TP/SL là tỷ lệ phần trăm của giá vào lệnh
                buy_tp_barrier  = entry_price * (1.0 + self.tp_pct + self.spread_pct)
                buy_sl_barrier  = entry_price * (1.0 - self.sl_pct + self.spread_pct)
                sell_tp_barrier = entry_price * (1.0 - self.tp_pct - self.spread_pct)
                sell_sl_barrier = entry_price * (1.0 + self.sl_pct - self.spread_pct)
            else:
                # Pip mode: Tính cả Spread vào cản
                buy_tp_barrier  = entry_price + self.tp_price + self.spread_price
                buy_sl_barrier  = entry_price - self.sl_price + self.spread_price
                sell_tp_barrier = entry_price - self.tp_price - self.spread_price
                sell_sl_barrier = entry_price + self.sl_price - self.spread_price

            limit_idx = min(i + 1 + self.max_hold_bars, n_rows)
            
            buy_result = 2  # 1=win, 0=loss, 2=pending
            sell_result = 2 # 1=win, 0=loss, 2=pending

            for j in range(i + 1, limit_idx):
                h = high_prices[j]
                l = low_prices[j]
                
                # Check lệnh BUY
                if buy_result == 2:
                    hit_buy_tp = h >= buy_tp_barrier
                    hit_buy_sl = l <= buy_sl_barrier
                    if hit_buy_tp and hit_buy_sl:
                        buy_result = 0 # Quét 2 đầu -> Tính thua cho an toàn
                    elif hit_buy_tp:
                        buy_result = 1 # Chạm TP
                    elif hit_buy_sl:
                        buy_result = 0 # Chạm SL
                        
                # Check lệnh SELL
                if sell_result == 2:
                    hit_sell_tp = l <= sell_tp_barrier
                    hit_sell_sl = h >= sell_sl_barrier
                    if hit_sell_tp and hit_sell_sl:
                        sell_result = 0 # Quét 2 đầu -> Tính thua cho an toàn
                    elif hit_sell_tp:
                        sell_result = 1
                    elif hit_sell_sl:
                        sell_result = 0
                        
                # Nếu cả 2 chiều đã có kết quả (thắng hoặc thua) thì không cần chạy tiếp các nến sau
                if buy_result != 2 and sell_result != 2:
                    break
                    
            # Gán nhãn cuối cùng
            if buy_result == 1 and sell_result != 1:
                labels[i] = 1 # Buy Win rõ ràng
            elif sell_result == 1 and buy_result != 1:
                labels[i] = 0 # Sell Win rõ ràng
            else:
                labels[i] = 2 # Cả 2 cùng thắng (mâu thuẫn) hoặc cả 2 cùng thua/timeout -> Sideway
                    
        return pd.Series(labels, index=df.index, name='target_class')

    # =========================================================
    # GIẢI PHÁP C: CLEAN DATA DIET
    # =========================================================
    def apply_triple_barrier_fast_hit(self, df, open_col, high_col, low_col,
                                       fast_hit_bars: int = 3):
        """
        [Giải Pháp C - Clean Data Diet]
        Giống apply_triple_barrier nhưng bổ sung thêm cột 'hit_bars':
        - hit_bars = số nến thực tế để chạm TP/SL.
        - hit_bars = -1 nếu Timeout (Sideway).

        Dùng kết hợp với get_clean_mask() để lọc tập Train chỉ giữ
        những Setup có sóng chắc chắn, dứt khoát (Chân Sóng Vĩ Đại).

        Args:
            df: DataFrame đã có cột OHLC
            open_col, high_col, low_col: Tên cột tương ứng
            fast_hit_bars: Ngưỡng "tốc độ sóng" (số nến tối đa để chạm TP).
                           VD: fast_hit_bars=3 -> chỉ giữ setup TP trong <=3 nến.

        Returns:
            DataFrame với 2 cột mới: 'target_class' và 'hit_bars'
        """
        labels   = np.full(len(df), 2, dtype=int)
        hit_bars = np.full(len(df), -1, dtype=int)   # -1 = Timeout/Sideway

        open_prices = df[open_col].values
        high_prices = df[high_col].values
        low_prices  = df[low_col].values
        n_rows = len(df)
        use_pct = (self.label_mode == 'pct')

        for i in range(n_rows - 1):
            entry_price = open_prices[i + 1]

            if use_pct:
                buy_tp_barrier  = entry_price * (1.0 + self.tp_pct + self.spread_pct)
                buy_sl_barrier  = entry_price * (1.0 - self.sl_pct + self.spread_pct)
                sell_tp_barrier = entry_price * (1.0 - self.tp_pct - self.spread_pct)
                sell_sl_barrier = entry_price * (1.0 + self.sl_pct - self.spread_pct)
            else:
                buy_tp_barrier  = entry_price + self.tp_price + self.spread_price
                buy_sl_barrier  = entry_price - self.sl_price + self.spread_price
                sell_tp_barrier = entry_price - self.tp_price - self.spread_price
                sell_sl_barrier = entry_price + self.sl_price - self.spread_price

            limit_idx = min(i + 1 + self.max_hold_bars, n_rows)
            
            buy_result = 2
            sell_result = 2
            
            buy_hit_bars = -1
            sell_hit_bars = -1

            for j in range(i + 1, limit_idx):
                h = high_prices[j]
                l = low_prices[j]
                
                if buy_result == 2:
                    hit_buy_tp = h >= buy_tp_barrier
                    hit_buy_sl = l <= buy_sl_barrier
                    if hit_buy_tp and hit_buy_sl:
                        buy_result = 0
                        buy_hit_bars = j - i
                    elif hit_buy_tp:
                        buy_result = 1
                        buy_hit_bars = j - i
                    elif hit_buy_sl:
                        buy_result = 0
                        buy_hit_bars = j - i
                        
                if sell_result == 2:
                    hit_sell_tp = l <= sell_tp_barrier
                    hit_sell_sl = h >= sell_sl_barrier
                    if hit_sell_tp and hit_sell_sl:
                        sell_result = 0
                        sell_hit_bars = j - i
                    elif hit_sell_tp:
                        sell_result = 1
                        sell_hit_bars = j - i
                    elif hit_sell_sl:
                        sell_result = 0
                        sell_hit_bars = j - i

                if buy_result != 2 and sell_result != 2:
                    break
                    
            if buy_result == 1 and sell_result != 1:
                labels[i] = 1
                hit_bars[i] = buy_hit_bars
            elif sell_result == 1 and buy_result != 1:
                labels[i] = 0
                hit_bars[i] = sell_hit_bars
            else:
                labels[i] = 2
                hit_bars[i] = -1

        return pd.DataFrame({
            'target_class': labels,
            'hit_bars': hit_bars
        }, index=df.index)

    def get_clean_mask(self, label_df, fast_hit_bars: int = 3,
                       include_sideway: bool = False):
        """
        [Giải Pháp C - Clean Data Diet]
        Tạo Boolean Mask từ DataFrame của apply_triple_barrier_fast_hit().

        Mask = True nếu:
        - Setup có hướng rõ ràng (Buy/Sell) VÀ chạm TP trong <= fast_hit_bars nến.
        - (Tùy chọn) Bao gồm Sideway nếu include_sideway=True.

        Ví dụ sử dụng:
            labeler = LabelingV3(...)
            label_df = labeler.apply_triple_barrier_fast_hit(df, open_col, high_col, low_col)
            mask = labeler.get_clean_mask(label_df, fast_hit_bars=3)
            X_clean = X[mask.values]
            Y_clean = label_df.loc[mask, 'target_class'].values
            print(f"Tập sạch: {mask.sum()}/{len(mask)} ({mask.mean()*100:.1f}%)")

        Args:
            label_df: DataFrame có cột 'target_class' và 'hit_bars'.
            fast_hit_bars: Số nến tối đa coi là "Chân Sóng Vĩ Đại".
            include_sideway: Có giữ mẫu Sideway trong Train không (mặc định False).

        Returns:
            pd.Series[bool] có cùng index với label_df.
        """
        is_decisive = label_df['target_class'].isin([0, 1])
        is_fast     = label_df['hit_bars'].between(1, fast_hit_bars)
        clean_mask  = is_decisive & is_fast

        if include_sideway:
            clean_mask = clean_mask | (label_df['target_class'] == 2)

        return clean_mask.rename('is_clean')
