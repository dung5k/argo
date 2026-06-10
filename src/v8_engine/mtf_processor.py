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
        
        # Rename columns to avoid collisions on open, high, low, close, volume while keeping existing suffixes
        rename_mid = {}
        for col in df_mid.columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                rename_mid[col] = f"{col}_mid"
            elif not col.endswith('_mid') and not col.endswith('_h1'):
                rename_mid[col] = f"{col}_mid"
        df_mid_renamed = df_mid.rename(columns=rename_mid)
        
        rename_high = {}
        for col in df_high.columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                rename_high[col] = f"{col}_high"
            elif not col.endswith('_high') and not col.endswith('_h4'):
                rename_high[col] = f"{col}_high"
        df_high_renamed = df_high.rename(columns=rename_high)
        
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
