import ccxt
import pandas as pd
import time
from datetime import datetime, timezone
import os
import sys
import concurrent.futures

def fetch_historical_data(symbol='BTC/USDT', timeframe='1m', since_str='2025-01-01T00:00:00Z'):
    # Tạo exchange instance local cho mỗi thread để đảm bảo an toàn bộ nhớ (Bật Rate Limit để tránh kẹt IP)
    exchange = ccxt.binance({'enableRateLimit': True})
    
    since_ts = exchange.parse8601(since_str)
    now_ts = exchange.milliseconds()
    all_ohlcv = []
    limit = 1000
    
    while since_ts < now_ts:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since_ts, limit)
            if not ohlcv:
                break
                
            all_ohlcv.extend(ohlcv)
            since_ts = ohlcv[-1][0] + 60000
            
        except ccxt.NetworkError as e:
            print(f"[{symbol}] NetworkError: {e}", flush=True)
            time.sleep(2)
        except Exception as e:
            print(f"[{symbol}] Exception: {e}", flush=True)
            break

    if not all_ohlcv:
        return symbol, pd.DataFrame()

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('datetime', inplace=True)
    df = df[df.index <= pd.to_datetime(now_ts, unit='ms')]
    
    return symbol, df

def save_to_parquet(df, filename):
    try:
        parquet_path = filename if filename.endswith('.parquet') else f"{filename}.parquet"
        df.to_parquet(parquet_path)
    except Exception as e:
        pass

def main():
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_path = os.path.join(base_path, "workspaces", "CFG_XAG_ASIAN_V6", "data", "raw")
    os.makedirs(data_path, exist_ok=True)
    os.chdir(data_path)
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 
               'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT']
    
    is_live = (len(sys.argv) > 1 and sys.argv[1] == "live")
    
    if is_live:
        one_day_ms = 86400 * 1000
        since_ts = int(time.time() * 1000) - one_day_ms
        since_str = datetime.fromtimestamp(since_ts/1000, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        since_str = '2025-01-01T00:00:00Z'
    
    # Lọc ra các symbol thực sự cần tải
    tasks = []
    for symbol in symbols:
        safe_filename = symbol.replace('/', '_').lower() + '_1m_2025_2026'
        file_path = os.path.join(data_path, f"{safe_filename}.parquet")
        
        if not is_live and os.path.exists(file_path):
            continue
            
        tasks.append((symbol, since_str))
        
    if tasks:
        # Giảm số luồng xuống 3 để tránh nghẽn API Rate-Limit của Binance làm treo lệnh
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_symbol = {executor.submit(fetch_historical_data, sym, '1m', since): sym for sym, since in tasks}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol, df = future.result()
                if not df.empty:
                    safe_filename = symbol.replace('/', '_').lower() + '_1m_2025_2026'
                    file_path = os.path.join(data_path, f"{safe_filename}.parquet")
                    save_to_parquet(df, file_path)
                    print(f"Lưu ThreadPool {symbol} thành công ({len(df)} nến).", flush=True)

if __name__ == "__main__":
    main()
