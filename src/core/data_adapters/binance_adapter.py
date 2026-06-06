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
            # Thử danh sách các mirror để tránh bị chặn/chập chờn
            mirrors = ['https://api.binance.com/api/v3', 'https://api1.binance.com/api/v3', 'https://api2.binance.com/api/v3', 'https://api3.binance.com/api/v3']
            # Ta sẽ xoay vòng mirror nếu cần, hoặc để CCXT tự xử lý fallback nếu cấu hình đúng
            # Ở đây ta set mặc định mirror đầu tiên, nhưng cho phép retry
            
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 5000, # Giảm timeout xuống 5s để tránh treo luồng quá lâu
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
        GIẢM LIMIT XUỐNG để tránh nặng tải (Chỉ cần đủ window cho AI).
        """
        if not self.exchange:
            if not self.connect(): return pd.DataFrame()
            
        # Tối ưu: Nếu AI chỉ cần window nhỏ (ví dụ 30, 60), không nên kéo 1000 nến
        fetch_limit = min(limit, 1000) # Tăng lên 1000 để hỗ trợ MTF 1H
        if fetch_limit < 100: fetch_limit = 100 # Tối thiểu 100 nến để tính Indicators
            
        # Chuẩn hoá mã "BTCUSDm" (của config) thành format của Binance "BTC/USDT"
        # Cải tiến: Hỗ trợ các cặp chéo như LTC/BTC
        if symbol.endswith("BTC") and symbol != "BTC":
            base_sym = symbol.replace("BTC", "").upper()
            binance_sym = base_sym + "/BTC"
        elif symbol.endswith("ETH") and symbol != "ETH":
            base_sym = symbol.replace("ETH", "").upper()
            binance_sym = base_sym + "/ETH"
        else:
            base_sym = symbol.replace("USDm", "").replace("USDT", "").replace("USD", "").upper()
            binance_sym = base_sym + "/USDT"
        
        # Đặc biệt cho BTCUSDT nếu base_sym rỗng
        if not base_sym and "BTC" in symbol: base_sym = "BTC"
        if binance_sym == "/USDT": binance_sym = "BTC/USDT"
        if binance_sym == "/BTC": binance_sym = "LTC/BTC" # Fallback an toàn cho LTCBTC nếu cần
        
        # Xử lý timeframe (MT5 gọi M1, CCXT gọi 1m)
        if timeframe.upper().startswith('M'):
            tf_ccxt = timeframe[1:] + 'm'
        elif timeframe.upper().startswith('H'):
            tf_ccxt = timeframe[1:] + 'h'
        elif timeframe.upper().startswith('D'):
            tf_ccxt = timeframe[1:] + 'd'
        else:
            tf_ccxt = timeframe.lower()
            
        # Thử 3 lần với các mirror khác nhau nếu lỗi
        mirrors = [None, 'api1.binance.com', 'api2.binance.com', 'api3.binance.com']
        last_err = ""
        
        for mirror in mirrors:
            try:
                if mirror:
                    self.exchange.hostname = mirror
                else:
                    self.exchange.hostname = 'api.binance.com'
                    
                raw_symbol = binance_sym.replace("/", "")
                if self.market_type in ['future', 'swap', 'delivery']:
                    klines = self.exchange.fapiPublicGetKlines({'symbol': raw_symbol, 'interval': tf_ccxt, 'limit': fetch_limit})
                else:
                    klines = self.exchange.publicGetKlines({'symbol': raw_symbol, 'interval': tf_ccxt, 'limit': fetch_limit})
                
                if not klines:
                    continue
                
                processed_klines = []
                for k in klines:
                    processed_klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'taker_buy_volume': float(k[9]),
                        'taker_sell_volume': float(k[5]) - float(k[9])
                    })
                    
                df = pd.DataFrame(processed_klines)
                df['time'] = df['timestamp'] / 1000.0  # seconds
                df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('datetime', inplace=True)
                
                # Cột giả lập cho MT5 Compatibility
                if 'real_volume' not in df.columns:
                    df['real_volume'] = df['volume']
                    
                # Đảm bảo index timezone = UTC
                df.index = df.index.tz_localize('UTC')
                
                # Thành công thì trả về ngay
                return df
                
            except Exception as e:
                last_err = str(e)
                self.log_message(f"⚠️ [Binance] Thử mirror {mirror if mirror else 'default'} thất bại: {last_err}")
                time.sleep(1) # Nghỉ 1s trước khi thử mirror tiếp theo
                
        self.log_message(f"❌ [Binance] TẤT CẢ MIRROR ĐỀU THẤT BẠI cho {binance_sym}: {last_err}")
        return pd.DataFrame()
        
    def fetch_historical_data(self, symbol: str, timeframe: str, start_time: str, end_time: str) -> pd.DataFrame:
        """
        Download dataset quá khứ (Có the tốn nhiều Request).
        """
        if not self.exchange:
            if not self.connect(): return pd.DataFrame()
            
        if symbol.endswith("BTC") and symbol != "BTC":
            base_sym = symbol.replace("BTC", "").upper()
            binance_sym = base_sym + "/BTC"
        else:
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
            
        if timeframe.upper().startswith('M'):
            tf_ccxt = timeframe[1:] + 'm'
        elif timeframe.upper().startswith('H'):
            tf_ccxt = timeframe[1:] + 'h'
        elif timeframe.upper().startswith('D'):
            tf_ccxt = timeframe[1:] + 'd'
        else:
            tf_ccxt = timeframe.lower()
        now_ts = self.exchange.milliseconds()
        if end_ts > now_ts: end_ts = now_ts

        all_ohlcv = []
        limit = 1000
        
        self.log_message(f"📥 [Binance] Bắt đầu cào {binance_sym} (từ {start_time})...")
        
        while since_ts < end_ts:
            try:
                raw_symbol = binance_sym.replace("/", "")
                if self.market_type in ['future', 'swap', 'delivery']:
                    klines = self.exchange.fapiPublicGetKlines({'symbol': raw_symbol, 'interval': tf_ccxt, 'startTime': since_ts, 'limit': limit})
                else:
                    klines = self.exchange.publicGetKlines({'symbol': raw_symbol, 'interval': tf_ccxt, 'startTime': since_ts, 'limit': limit})
                    
                if not klines:
                    break
                    
                processed_klines = []
                for k in klines:
                    processed_klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'taker_buy_volume': float(k[9]),
                        'taker_sell_volume': float(k[5]) - float(k[9])
                    })
                    
                # Có thể api trả về lố qua end_ts, lọc sạch rác ở khúc nối
                processed_klines = [k for k in processed_klines if k['timestamp'] <= end_ts]
                if not processed_klines:
                    break
                    
                all_ohlcv.extend(processed_klines)
                # Dịch con trỏ thời gian đi + 1 frame
                since_ts = processed_klines[-1]['timestamp'] + 60000 
                
            except ccxt.NetworkError as e:
                self.log_message(f"[{binance_sym}] NetworkError: {e}")
                time.sleep(2)
            except Exception as e:
                self.log_message(f"[{binance_sym}] Exception: {e}")
                break
                
        if not all_ohlcv:
            return pd.DataFrame()
            
        df = pd.DataFrame(all_ohlcv)
        df['time'] = df['timestamp'] / 1000.0  # seconds
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('datetime', inplace=True)
        # Giả lập volume
        df['real_volume'] = df['volume']
        
        df.index = df.index.tz_localize('UTC')
        return df
