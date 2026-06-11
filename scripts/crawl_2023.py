import os
import sys
import pandas as pd
from datetime import datetime, timezone
import MetaTrader5 as mt5

print("Connecting to MT5...")
if not mt5.initialize():
    print("initialize() failed, error code =", mt5.last_error())
    quit()

symbol = "XAUUSDm"
print(f"Fetching data for {symbol}...")

start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)

rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_date, end_date)

if rates is None or len(rates) == 0:
    print(f"Failed to fetch data or no data returned. Error: {mt5.last_error()}")
else:
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'XAUUSDm_M1_2023_2026.parquet')
    df.to_parquet(out_path)
    print(f"Saved {len(df)} rows to {out_path}")
    print(f"Date range: {df.index.min()} to {df.index.max()}")

mt5.shutdown()
