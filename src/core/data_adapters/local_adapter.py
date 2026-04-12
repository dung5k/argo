import pandas as pd
import os
from src.core.data_adapters.base_adapter import BaseDataAdapter

class LocalAdapter(BaseDataAdapter):
    """
    Adapter kết nối lấy dữ liệu từ các file Local Parquet.
    """
    
    def __init__(self, data_dir: str, log_callback=print):
        super().__init__(log_callback)
        self.data_dir = data_dir
        
    def connect(self) -> bool:
        return os.path.exists(self.data_dir)
        
    def fetch_live_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        Đọc file Parquet local và lấy N nến cuối cùng.
        """
        pq_path, clean_sym = self._resolve_local_file(symbol)
        
        if pq_path and os.path.exists(pq_path):
            try:
                df = pd.read_parquet(pq_path)
                df = df.tail(limit).copy()
                
                # Đảm bảo có cột time theo chuẩn
                if df.index.name == 'datetime' or isinstance(df.index, pd.DatetimeIndex):
                    df['time'] = df.index.astype(int) / 10**9 # Convert to unix
                df['datetime'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('datetime', inplace=True)
                
                if df.index.tz is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')
                    
                return df
            except Exception as e:
                self.log_message(f"⚠️ Lỗi đọc LOCAL Parquet cho {symbol}: {e}")
                
        return pd.DataFrame()
        
    def fetch_historical_data(self, symbol: str, timeframe: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        Đọc toàn bộ file.
        """
        pq_path, clean_sym = self._resolve_local_file(symbol)
        if pq_path and os.path.exists(pq_path):
            try:
                df = pd.read_parquet(pq_path)
                if df.index.name == 'datetime' or isinstance(df.index, pd.DatetimeIndex):
                    df['time'] = df.index.astype(int) / 10**9
                df['datetime'] = pd.to_datetime(df['time'], unit='s')
                df.set_index('datetime', inplace=True)
                if df.index.tz is None: df.index = df.index.tz_localize('UTC')
                else: df.index = df.index.tz_convert('UTC')
                
                start_dt = pd.to_datetime(start_time).tz_localize('UTC')
                end_dt = pd.to_datetime(end_time).tz_localize('UTC') + pd.Timedelta(days=1)
                df = df[(df.index >= start_dt) & (df.index <= end_dt)]
                return df
            except Exception as e:
                self.log_message(f"⚠️ Lỗi đọc LOCAL Parquet cho {symbol}: {e}")
                
        return pd.DataFrame()

    def _resolve_local_file(self, symbol: str):
        sym_clean_upper = symbol.replace("m", "").upper()
        clean_sym = symbol.replace("m", "").lower()
        
        pq_name = sym_clean_upper
        pq_path = os.path.join(self.data_dir, pq_name)
        if not os.path.exists(pq_path):
            pq_path_2 = os.path.join(self.data_dir, f"{clean_sym}_mt5_1m_2026.parquet")
            if os.path.exists(pq_path_2): 
                pq_path = pq_path_2
            else:
                # Fallback to broad scan for any file matching name
                for file in os.listdir(self.data_dir):
                    if clean_sym in file.lower() and file.endswith('.parquet'):
                        pq_path = os.path.join(self.data_dir, file)
                        break
                        
        return pq_path, clean_sym
