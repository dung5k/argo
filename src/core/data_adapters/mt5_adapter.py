import pandas as pd
import MetaTrader5 as mt5
import time
from datetime import datetime
import os
from src.core.data_adapters.base_adapter import BaseDataAdapter

class MT5Adapter(BaseDataAdapter):
    """
    Adapter kết nối lấy dữ liệu từ phần mềm MetaTrader 5 (MT5).
    """
    
    def __init__(self, executable_path: str, log_callback=print):
        super().__init__(log_callback)
        self.terminal_path = executable_path
        self.is_connected = False
        
    def connect(self) -> bool:
        if self.is_connected:
            return True
            
        mt5.shutdown()
        if not mt5.initialize(path=self.terminal_path):
            self.log_message(f"❌ [MT5] Không thể khởi tạo MT5 tại {self.terminal_path}")
            return False
            
        self.is_connected = True
        return True
        
    def disconnect(self) -> None:
        if self.is_connected:
            mt5.shutdown()
            self.is_connected = False
            
    def _get_timezone_offset(self, symbol: str) -> int:
        """
        Giao thức lấy độ lệch giờ của Terminal MT5 hiện tại so với Server/UTC.
        """
        offset_hours = 3 # Mặc định thường là 3 (Exness)
        if mt5.symbol_select(symbol, True):
            tick = mt5.symbol_info_tick(symbol)
            if tick and tick.time > 0:
                diff_h = round((tick.time - int(time.time())) / 3600)
                if abs(diff_h) <= 14:
                    offset_hours = diff_h
        return offset_hours

    def fetch_live_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        if not self.connect():
            return pd.DataFrame()
            
        tf_map = {
            'M1': mt5.TIMEFRAME_M1,
            'H1': mt5.TIMEFRAME_H1
        }
        mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M1)
        
        # Mở symbol
        if not mt5.symbol_select(symbol, True):
            return pd.DataFrame()
            
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, limit)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        
        # Căn chỉnh timezone giống bản cũ
        offset_hours = self._get_timezone_offset(symbol)
        df['time'] = df['time'] - (offset_hours * 3600)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('datetime', inplace=True)
        # Đưa về UTC chuẩn
        df.index = df.index.tz_localize('UTC')
        
        df.drop(columns=['spread'], inplace=True, errors='ignore')
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        return df
        
    def fetch_historical_data(self, symbol: str, timeframe: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        Trong MT5, tốt nhất dùng copy_rates_from_pos với số lượng lớn thay vì range do lỗi server MT5.
        Tính năng này thường được wrap bởi vòng lặp cuộn (Stitching) của DataManager 
        nhưng adapter sẽ cung cấp hàm lấy raw từ vị trí date.
        """
        if not self.connect():
            return pd.DataFrame()
            
        tf_map = {'M1': mt5.TIMEFRAME_M1, 'H1': mt5.TIMEFRAME_H1}
        mt5_tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_M1)
        
        if not mt5.symbol_select(symbol, True):
            return pd.DataFrame()

        # Dùng tính toán ngày để lấy N nến
        try:
            start_dt = pd.to_datetime(start_time)
            end_dt = pd.to_datetime(end_time)
            delta_days = (end_dt - start_dt).days + 3
            if timeframe.upper() == 'M1':
                max_bars = delta_days * 24 * 60
            else:
                max_bars = delta_days * 24
                
            rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, max_bars)
            if rates is None or len(rates) == 0:
                return pd.DataFrame()
                
            df = pd.DataFrame(rates)
            offset = self._get_timezone_offset(symbol)
            df['datetime'] = pd.to_datetime(df['time'] - (offset * 3600), unit='s')
            df.set_index('datetime', inplace=True)
            df.index = df.index.tz_localize('UTC')
            
            # Filter the dates accurately
            df = df[(df.index >= start_dt.tz_localize('UTC')) & (df.index <= end_dt.tz_localize('UTC') + pd.Timedelta(days=1))]
            df.drop(columns=['spread'], inplace=True, errors='ignore')
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)
            
            return df
        except Exception as e:
            self.log_message(f"Lỗi fetch lịch sử MT5 {symbol}: {e}")
            return pd.DataFrame()
