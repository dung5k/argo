import pandas as pd
import numpy as np

class OrderBlockDetector:
    """
    Phát hiện và quản lý Order Block (OB) chưa Mitigated.
    Dựa trên tín hiệu BOS/CHOCH từ NLPTokenizer.
    """
    def __init__(self, config: dict):
        params = config.get('fractal_params', {})
        self.atr_period = 14
        self.min_atr_multiplier = 2.0 # Độ dài sóng Impulse tối thiểu so với ATR
        self.max_ob_memory = 10 # Giới hạn mảng OB

    def _calc_atr(self, df: pd.DataFrame) -> pd.Series:
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.atr_period).mean()

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        
        if 'market_structure_token' not in df_out.columns:
            raise ValueError("Phải chạy qua NLPTokenizer trước khi tìm OB.")
            
        df_out['atr'] = self._calc_atr(df_out)
        
        # Output features
        in_ob_up = np.zeros(len(df_out))
        in_ob_dn = np.zeros(len(df_out))
        ob_strength = np.zeros(len(df_out))
        
        # State arrays
        # Unmitigated Demand OBs (Bullish) - chờ giá giảm xuống chạm
        demand_obs = [] 
        # Unmitigated Supply OBs (Bearish) - chờ giá tăng lên chạm
        supply_obs = []
        
        # Helper function để tìm cây nến tạo gốc sóng
        def find_ob_candle(idx, is_bullish):
            # Lùi lại tối đa 20 nến để tìm nến ngược màu cuối cùng
            start_i = max(0, idx - 20)
            for i in range(idx-1, start_i, -1):
                if is_bullish:
                    # Tìm nến giảm (open > close)
                    if df_out['open'].iloc[i] > df_out['close'].iloc[i]:
                        return df_out['high'].iloc[i], df_out['low'].iloc[i]
                else:
                    # Tìm nến tăng (close > open)
                    if df_out['close'].iloc[i] > df_out['open'].iloc[i]:
                        return df_out['high'].iloc[i], df_out['low'].iloc[i]
            return None, None

        prev_fractal_high = np.nan
        prev_fractal_low = np.nan

        # Scan
        for i in range(len(df_out)):
            row = df_out.iloc[i]
            token = row['market_structure_token']
            
            # Cập nhật các mức Fractal gần nhất để tính độ dài Impulse
            if row.get('is_fh_confirmed', False) and not pd.isna(row.get('fractal_high_val')):
                prev_fractal_high = row['fractal_high_val']
            if row.get('is_fl_confirmed', False) and not pd.isna(row.get('fractal_low_val')):
                prev_fractal_low = row['fractal_low_val']

            # 1. Mitigation Check (Xóa OB khi bị chạm)
            curr_low = row['low']
            curr_high = row['high']
            
            # Kiểm tra Demand OBs (Giá chạm từ trên xuống)
            surviving_demand = []
            for ob in demand_obs:
                top, bottom, strength = ob
                if curr_low <= top:
                    # Đã chạm! Ghi nhận tín hiệu In_OB
                    in_ob_up[i] = 1.0
                    ob_strength[i] = max(ob_strength[i], strength)
                    # Bị mitigate -> không cho vào surviving
                else:
                    surviving_demand.append(ob)
            demand_obs = surviving_demand

            # Kiểm tra Supply OBs (Giá chạm từ dưới lên)
            surviving_supply = []
            for ob in supply_obs:
                top, bottom, strength = ob
                if curr_high >= bottom:
                    # Đã chạm!
                    in_ob_dn[i] = 1.0
                    ob_strength[i] = max(ob_strength[i], strength)
                else:
                    surviving_supply.append(ob)
            supply_obs = surviving_supply

            # 2. Tạo OB mới nếu có Breakout mạnh
            if pd.notna(token) and "BOS" in str(token) or "CHOCH" in str(token):
                if token in ["BOS_UP", "CHOCH_UP"] and not pd.isna(prev_fractal_low):
                    impulse_length = row['close'] - prev_fractal_low
                    atr_val = row['atr']
                    if atr_val > 0 and impulse_length > self.min_atr_multiplier * atr_val:
                        # Hợp lệ! Tìm OB candle
                        top, bottom = find_ob_candle(i, is_bullish=True)
                        if top is not None:
                            strength = impulse_length / atr_val
                            demand_obs.append((top, bottom, strength))
                            if len(demand_obs) > self.max_ob_memory:
                                demand_obs.pop(0)
                                
                elif token in ["BOS_DN", "CHOCH_DN"] and not pd.isna(prev_fractal_high):
                    impulse_length = prev_fractal_high - row['close']
                    atr_val = row['atr']
                    if atr_val > 0 and impulse_length > self.min_atr_multiplier * atr_val:
                        top, bottom = find_ob_candle(i, is_bullish=False)
                        if top is not None:
                            strength = impulse_length / atr_val
                            supply_obs.append((top, bottom, strength))
                            if len(supply_obs) > self.max_ob_memory:
                                supply_obs.pop(0)

        df_out['in_ob_up'] = in_ob_up
        df_out['in_ob_dn'] = in_ob_dn
        df_out['ob_strength'] = ob_strength
        return df_out
