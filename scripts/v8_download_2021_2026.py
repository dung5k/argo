import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def main():
    mt5_path = "D:/mt5/MetaTrader 5 EXNESS/terminal64.exe"
    print(f"Connecting to MT5 at {mt5_path}...")
    if not mt5.initialize(mt5_path):
        print(f"MT5 initialize failed, error code: {mt5.last_error()}")
        return

    symbol = "XAUUSDm"
    if not mt5.symbol_select(symbol, True):
        symbol = "XAUUSD"
        if not mt5.symbol_select(symbol, True):
            print("Failed to select XAUUSDm or XAUUSD")
            mt5.shutdown()
            return

    print(f"Selected symbol: {symbol}")
    
    timezone = pytz.timezone("Etc/UTC")
    
    # Define yearly chunks
    chunks = [
        (datetime(2021, 1, 1, tzinfo=timezone), datetime(2022, 1, 1, tzinfo=timezone)),
        (datetime(2022, 1, 1, tzinfo=timezone), datetime(2023, 1, 1, tzinfo=timezone)),
        (datetime(2023, 1, 1, tzinfo=timezone), datetime(2024, 1, 1, tzinfo=timezone)),
        (datetime(2024, 1, 1, tzinfo=timezone), datetime(2025, 1, 1, tzinfo=timezone)),
        (datetime(2025, 1, 1, tzinfo=timezone), datetime(2026, 6, 10, tzinfo=timezone))
    ]
    
    all_dfs = []
    
    for idx, (start, end) in enumerate(chunks):
        print(f"Downloading chunk {idx+1}: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}...")
        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
        
        if rates is None or len(rates) == 0:
            print(f"⚠️ No data returned for chunk {idx+1}. Error: {mt5.last_error()}")
            # Retry once
            print("Retrying chunk...")
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
            if rates is None or len(rates) == 0:
                print(f"❌ Failed chunk {idx+1} after retry. Skipping.")
                continue
                
        df_chunk = pd.DataFrame(rates)
        df_chunk['time'] = pd.to_datetime(df_chunk['time'], unit='s')
        df_chunk.set_index('time', inplace=True)
        all_dfs.append(df_chunk)
        print(f"Chunk {idx+1} retrieved: {len(df_chunk)} bars.")
        
    if not all_dfs:
        print("❌ No data was downloaded at all.")
        mt5.shutdown()
        return
        
    print("Combining all chunks...")
    df_all = pd.concat(all_dfs)
    df_all = df_all[~df_all.index.duplicated(keep='first')].sort_index()
    
    out_path = "data/XAUUSDm_M1_2021_2026.parquet"
    os.makedirs("data", exist_ok=True)
    df_all.to_parquet(out_path)
    
    print(f"✅ Successfully downloaded {len(df_all)} M1 bars.")
    print(f"Saved to {out_path} (Size: {os.path.getsize(out_path)/1024/1024:.2f} MB)")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
