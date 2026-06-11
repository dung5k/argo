import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz
import os

if not mt5.initialize():
    print("MT5 initialize failed", mt5.last_error())
    quit()

timezone = pytz.timezone("Etc/UTC")
start_time = datetime(2024, 1, 1, tzinfo=timezone)
end_time = datetime(2026, 6, 9, tzinfo=timezone)

symbol = "XAUUSDm"

if not mt5.symbol_select(symbol, True):
    print(f"Failed to select {symbol}")
    mt5.shutdown()
    quit()

print(f"Requesting {symbol} M1 data from {start_time} to {end_time}...")
rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_time, end_time)

if rates is None or len(rates) == 0:
    print(f"No M1 data found for {symbol} in MT5, error: {mt5.last_error()}")
else:
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    # Set time as index for fast querying
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)
    
    out_path = "data/XAUUSDm_M1_2024_2026.parquet"
    df.to_parquet(out_path)
    
    print(f"Successfully retrieved {len(df)} M1 bars for {symbol}.")
    print(f"Saved to {out_path}")

mt5.shutdown()
