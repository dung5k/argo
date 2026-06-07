import pandas as pd

class MTFProcessor:
    """
    Xử lý Đồng pha Đa khung thời gian (MTF).
    Nghiêm cấm Look-ahead bias: Left Join M15 với H1/H4 bắt buộc dùng ffill (forward fill),
    và chỉ join với các nến H1/H4 ĐÃ ĐÓNG CỬA hoàn toàn.
    """
    def __init__(self, config: dict):
        pass

    def merge_mtf(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame, df_h4: pd.DataFrame) -> pd.DataFrame:
        """
        Gộp dữ liệu M15 với H1 và H4.
        Yêu cầu Index của DataFrames phải là DatetimeIndex.
        Giả định Timestamp trên Index là thời điểm BẮT ĐẦU nến.
        """
        if not isinstance(df_m15.index, pd.DatetimeIndex):
            raise ValueError("M15 Index phải là DatetimeIndex")
            
        df_m15 = df_m15.sort_index()
        df_h1 = df_h1.sort_index()
        df_h4 = df_h4.sort_index()
        
        df_h1_renamed = df_h1.add_suffix('_h1')
        df_h4_renamed = df_h4.add_suffix('_h4')
        
        # Dịch chuyển Index của H1/H4 từ "Thời điểm mở nến" sang "Thời điểm đóng nến"
        # Để đảm bảo nến M15 tại 14:15 chỉ map với nến H1 đã đóng lúc 14:00 (tức là nến mở lúc 13:00)
        df_h1_closed = df_h1_renamed.copy()
        df_h1_closed.index = df_h1_closed.index + pd.Timedelta(hours=1)
        
        df_h4_closed = df_h4_renamed.copy()
        df_h4_closed.index = df_h4_closed.index + pd.Timedelta(hours=4)
        
        # Merge_asof backward
        merged = pd.merge_asof(
            df_m15, 
            df_h1_closed, 
            left_index=True, 
            right_index=True, 
            direction='backward'
        )
        
        merged = pd.merge_asof(
            merged, 
            df_h4_closed, 
            left_index=True, 
            right_index=True, 
            direction='backward'
        )
        
        return merged
