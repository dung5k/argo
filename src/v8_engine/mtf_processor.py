import pandas as pd

class MTFProcessor:
    """
    Xử lý Đồng pha Đa khung thời gian (MTF).
    Nghiêm cấm Look-ahead bias: Left Join M15 với H1/H4 bắt buộc dùng ffill (forward fill),
    và chỉ join với các nến H1/H4 ĐÃ ĐÓNG CỬA hoàn toàn.
    """
    def __init__(self, config: dict):
        pass

    def merge_mtf(self, df_base: pd.DataFrame, df_mid: pd.DataFrame, df_high: pd.DataFrame) -> pd.DataFrame:
        """
        Gộp dữ liệu Base với Mid và High.
        Yêu cầu Index của DataFrames phải là DatetimeIndex.
        Giả định Timestamp trên Index là thời điểm BẮT ĐẦU nến.
        """
        if not isinstance(df_base.index, pd.DatetimeIndex):
            raise ValueError("Base Index phải là DatetimeIndex")
            
        df_base = df_base.sort_index()
        df_mid = df_mid.sort_index()
        df_high = df_high.sort_index()
        
        df_mid_renamed = df_mid.add_suffix('_mid')
        df_high_renamed = df_high.add_suffix('_high')
        
        # Dịch chuyển Index của Mid/High từ "Thời điểm mở nến" sang "Thời điểm đóng nến"
        mid_delta = df_mid.index[1] - df_mid.index[0] if len(df_mid) > 1 else pd.Timedelta(hours=1)
        high_delta = df_high.index[1] - df_high.index[0] if len(df_high) > 1 else pd.Timedelta(hours=4)
        
        df_mid_closed = df_mid_renamed.copy()
        df_mid_closed.index = df_mid_closed.index + mid_delta
        
        df_high_closed = df_high_renamed.copy()
        df_high_closed.index = df_high_closed.index + high_delta
        
        # Merge_asof backward
        merged = pd.merge_asof(
            df_base, 
            df_mid_closed, 
            left_index=True, 
            right_index=True, 
            direction='backward'
        )
        
        merged = pd.merge_asof(
            merged, 
            df_high_closed, 
            left_index=True, 
            right_index=True, 
            direction='backward'
        )
        
        return merged
