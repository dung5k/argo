import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import os
import sys

# Vì chạy trong sys.path, import từ peer module
from src.core.data_adapters.base_adapter import BaseDataAdapter

class BinanceAdapter(BaseDataAdapter):
    """
    Adapter kết nối trực tiếp với Binance (Spot/Futures) bằng CCXT.
    """
    
    def __init__(self, log_callback=print, **kwargs):
        super().__init__(log_callback)
        self.exchange = None
        self.market_type = kwargs.get('market_type', 'spot') # hoặc 'future' / 'swap'
        
    def connect(self) -> bool:
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': self.market_type,
                }
            })
            return True
        except Exception as e:
            self.log_message(f"Lỗi khởi tạo CCXT Binance: {e}")
            return False
            
    def disconnect(self) -> None:
        pass
        
    def fetch_live_data(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """
        Pull LIVE candles từ Binance.
        CCXT Binance nhận limit tối đa 1000.
        """
        if not self.exchange:
            if not self.connect(): return pd.DataFrame()
            
        # Chuẩn hoá mã "BTCUSDm" (của config) thành format của Binance "BTC/USDT"
        # config routing thường để dict như: "BTCUSD": "BINANCE". Target là symbol gốc từ MT5 mapping
        base_sym = symbol.replace("USDm", "").replace("USDT", "").replace("USD", "").upper()
        binance_sym = base_sym + "/USDT"
        
        # Xử lý timeframe (MT5 gọi M1, CCXT gọi 1m)
        if timeframe == 'M1': 
            tf_ccxt = '1m'
        elif timeframe == 'H1':
            tf_ccxt = '1h'
        else:
            tf_ccxt = timeframe.lower()
            
        try:
            ohlcv = self.exchange.fetch_ohlcv(binance_sym, tf_ccxt, limit=limit)
            if not ohlcv:
                return pd.DataFrame()
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['time'] = df['timestamp'] / 1000.0  # seconds
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('datetime', inplace=True)
            
            # Cột giả lập cho MT5 Compatibility
            if 'real_volume' not in df.columns:
                df['real_volume'] = df['volume']
                
            # Đảm bảo index timezone = UTC
            df.index = df.index.tz_localize('UTC')
            return df
            
        except Exception as e:
            self.log_message(f"⚠️ [Binance] Lỗi tải nến live {binance_sym}: {e}")
            return pd.DataFrame()
            
    def fetch_historical_data(self, symbol: str, timeframe: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        Download dataset quá khứ (Có the tốn nhiều Request).
        """
        if not self.exchange:
            if not self.connect(): return pd.DataFrame()
            
        base_sym = symbol.replace("USDm", "").replace("USDT", "").replace("USD", "").upper()
        binance_sym = base_sym + "/USDT"
        
        # Format time
        from dateutil import parser
        try:
            start_dt = parser.parse(start_time)
            # Chuyển về ms Timestamp
            since_ts = int(start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
            
            end_dt = parser.parse(end_time)
            end_ts = int(end_dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
            
        except Exception as e:
            self.log_message(f"Lỗi format ngày tháng Binance: {e}")
            return pd.DataFrame()
            
        tf_ccxt = '1m' if timeframe.upper() == 'M1' else timeframe.lower()
        now_ts = self.exchange.milliseconds()
        if end_ts > now_ts: end_ts = now_ts

        all_ohlcv = []
        limit = 1000
        
        self.log_message(f"📥 [Binance] Bắt đầu cào {binance_sym} (từ {start_time})...")
        
        while since_ts < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(binance_sym, tf_ccxt, since_ts, limit)
                if not ohlcv:
                    break
                    
                # Có thể api trả về lố qua end_ts, lọc sạch rác ở khúc nối
                ohlcv = [o for o in ohlcv if o[0] <= end_ts]
                if not ohlcv:
                    break
                    
                all_ohlcv.extend(ohlcv)
                # Dịch con trỏ thời gian đi + 1 frame
                since_ts = ohlcv[-1][0] + 60000 
                
            except ccxt.NetworkError as e:
                self.log_message(f"[{binance_sym}] NetworkError: {e}")
                time.sleep(2)
            except Exception as e:
                self.log_message(f"[{binance_sym}] Exception: {e}")
                break
                
        if not all_ohlcv:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = df['timestamp'] / 1000.0  # seconds
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        # Giả lập volume
        df['real_volume'] = df['volume']
        
        df.index = df.index.tz_localize('UTC')
        return df
