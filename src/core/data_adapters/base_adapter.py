import pandas as pd
from typing import Optional, Tuple, Any

class BaseDataAdapter:
    """
    Interface cơ sở cho mọi nguồn dữ liệu (MT5, Binance, Local Parquet).
    Tất cả các adapter đều phải tuân thủ chuẩn này để router gọi đồng nhất.
    """
    
    def __init__(self, log_callback=print):
        self.log_message = log_callback
        
    def connect(self) -> bool:
        """
        Khởi tạo kết nối đến nguồn dữ liệu.
        Trả về True nếu thành công, False nếu lỗi.
        """
        raise NotImplementedError
        
    def disconnect(self) -> None:
        """
        Đóng kết nối (nếu cần).
        """
        pass
        
    def fetch_live_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        Rút N nến gần nhất phục vụ cho Live Trading.
        
        Yêu cầu Output DataFrame:
        - Index: Tên là 'datetime' (pd.DatetimeIndex), timezone UTC.
        - Các cột: 'open', 'high', 'low', 'close', 'volume', 'real_volume', 'time' (Unix timestamp).
        """
        raise NotImplementedError
        
    def fetch_historical_data(self, symbol: str, timeframe: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        Tải toàn bộ số lượng lớn nến trong khoảng thời gian để Training lịch sử.
        start_time, end_time format gốc: "2025-01-01"
        """
        raise NotImplementedError
