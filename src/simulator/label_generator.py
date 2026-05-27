import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TripleBarrierLabeler:
    """
    Gán nhãn dữ liệu M1 theo Triple Barrier Method của Marcos Lopez de Prado.
    Nhãn trả về:
       1: BUY thành công (Chạm TP trước)
      -1: SELL thành công (Chạm TP trước)
       0: HOLD/RÁC (Chạm SL hoặc Hết giờ Max Hold mà chưa đủ lãi)
    """
    def __init__(self, point: float, sl_pips: float, tp_pips: float, max_hold_bars: int, slippage_pips: float = 1.0, default_spread_pips: float = 1.5):
        self.point = point
        self.sl_dist = sl_pips * point * 10
        self.tp_dist = tp_pips * point * 10
        self.slippage = slippage_pips * point * 10
        self.default_spread = default_spread_pips * point * 10
        self.max_hold = max_hold_bars

    def generate_labels(self, df: pd.DataFrame, prefix: str = "XAGUSD") -> pd.DataFrame:
        logger.info("Bắt đầu gán nhãn Triple Barrier (Numpy Engine)...")
        
        # 1. Chuyển sang Numpy Arrays để đạt tốc độ C-level
        # Lưu ý: Cột spread nên có sẵn, nếu không có thì dùng default
        opens = df[f'{prefix}_open'].values
        highs = df[f'{prefix}_high'].values
        lows = df[f'{prefix}_low'].values
        closes = df[f'{prefix}_close'].values
        
        spreads = df[f'{prefix}_spread'].values if f'{prefix}_spread' in df.columns else np.full(len(df), self.default_spread)
        # Nếu spread trong data lưu bằng points, chuyển về giá trị tuyệt đối
        if spreads.max() > 100: 
            spreads = spreads * self.point 

        n = len(df)
        labels = np.zeros(n, dtype=np.int8)
        
        # 2. Vectorized Forward Sweep
        # (Để tối ưu tuyệt đối ở Production, anh nên wrap hàm này bằng @njit của Numba)
        for i in range(n - self.max_hold - 1):
            # Tính giá khớp lệnh ở nến T+1 (Cộng Slippage và Spread)
            t_entry = i + 1
            
            # --- KIỂM TRA LỆNH BUY ---
            # Mua tại giá Ask (Open + Spread) + bị trượt giá lên trên
            buy_entry_price = opens[t_entry] + spreads[t_entry] + self.slippage
            buy_tp_level = buy_entry_price + self.tp_dist
            buy_sl_level = buy_entry_price - self.sl_dist
            
            buy_result = 0 # Mặc định là Hold/Thất bại
            
            for hold_bar in range(self.max_hold):
                curr_idx = t_entry + hold_bar
                # Quét giá Bid cho lệnh BUY đóng
                c_high = highs[curr_idx]
                c_low = lows[curr_idx]
                
                hit_sl = c_low <= buy_sl_level
                hit_tp = c_high >= buy_tp_level
                
                if hit_sl and hit_tp:
                    # PESSIMISTIC: Nếu chạm cả 2 trong 1 nến M1, tự động tính là cắn SL trước!
                    break # buy_result vẫn là 0
                elif hit_sl:
                    break
                elif hit_tp:
                    buy_result = 1
                    break
                    
            # --- KIỂM TRA LỆNH SELL ---
            # Bán tại giá Bid (Open) - bị trượt giá xuống dưới
            sell_entry_price = opens[t_entry] - self.slippage
            sell_tp_level = sell_entry_price - self.tp_dist
            sell_sl_level = sell_entry_price + self.sl_dist
            
            sell_result = 0
            
            for hold_bar in range(self.max_hold):
                curr_idx = t_entry + hold_bar
                # Đóng lệnh SELL bằng giá Ask (Đỉnh/Đáy + Spread)
                c_ask_high = highs[curr_idx] + spreads[curr_idx]
                c_ask_low = lows[curr_idx] + spreads[curr_idx]
                
                hit_sl = c_ask_high >= sell_sl_level
                hit_tp = c_ask_low <= sell_tp_level
                
                if hit_sl and hit_tp:
                    break # Cắn SL trước
                elif hit_sl:
                    break
                elif hit_tp:
                    sell_result = -1
                    break

            # 3. Ghi nhãn xung đột (Conflict Resolution)
            # Rất hiếm khi cả BUY và SELL cùng chạm TP hợp lệ (thường do thị trường giật 2 chiều cực mạnh)
            # Nếu xảy ra, gán nhãn 0 (Rác) để tránh nhiễu model.
            if buy_result == 1 and sell_result == -1:
                labels[i] = 0
            elif buy_result == 1:
                labels[i] = 1
            elif sell_result == -1:
                labels[i] = -1
            else:
                labels[i] = 0

        # Lưu lại vào DataFrame
        df['target_label'] = labels
        
        # Thống kê
        buy_cnt = np.sum(labels == 1)
        sell_cnt = np.sum(labels == -1)
        hold_cnt = np.sum(labels == 0)
        logger.info(f"Hoàn tất! Phân bổ nhãn: BUY={buy_cnt}, SELL={sell_cnt}, HOLD={hold_cnt}")
        
        return df
