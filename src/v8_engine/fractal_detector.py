import pandas as pd
import numpy as np

class FractalDetector:
    """
    Phát hiện các đỉnh/đáy Fractal theo định nghĩa của Bill Williams (Window nến động).
    Đảm bảo 100% Data Integrity: Tín hiệu tại nến T chỉ được dựa trên dữ liệu từ T trở về trước.
    """
    def __init__(self, window_size: int = 5, latency_candles: int = 2):
        if window_size % 2 == 0 or window_size < 3:
            raise ValueError("Window size phải là số lẻ >= 3 (ví dụ: 3, 5, 7)")
        self.window_size = window_size
        self.latency = window_size // 2

    def detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input: DataFrame có ít nhất các cột 'high', 'low'
        Output: DataFrame được bổ sung thêm các cột trạng thái
        """
        df_out = df.copy()
        
        if 'high' not in df_out.columns or 'low' not in df_out.columns:
            raise ValueError("DataFrame phải chứa cột 'high' và 'low'")

        h = df_out['high']
        l = df_out['low']

        pivot_h = h.shift(self.latency)
        pivot_l = l.shift(self.latency)

        cond_fh = pd.Series(True, index=df_out.index)
        cond_fl = pd.Series(True, index=df_out.index)

        for i in range(self.window_size):
            shift_val = self.window_size - 1 - i
            if shift_val != self.latency:
                cond_fh = cond_fh & (pivot_h > h.shift(shift_val))
                cond_fl = cond_fl & (pivot_l < l.shift(shift_val))

        df_out['is_fh_confirmed'] = cond_fh
        df_out['is_fl_confirmed'] = cond_fl

        df_out['fractal_high_val'] = np.where(cond_fh, pivot_h, np.nan)
        df_out['fractal_low_val'] = np.where(cond_fl, pivot_l, np.nan)

        return df_out
