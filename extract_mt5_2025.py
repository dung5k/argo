import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os

mt5_path = "C:/Program Files/MetaTrader 5/terminal64.exe"
print(f"Connecting to MT5: {mt5_path}")
if not mt5.initialize(mt5_path):
    print("MT5 init failed, error code =", mt5.last_error())
    quit()

symbols = ["XAGUSDm", "XAUUSD", "DXY"]
start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
end_date = datetime.now(timezone.utc)

out_dir = "temp_mt5_raw"
os.makedirs(out_dir, exist_ok=True)

for sym in symbols:
    print(f"Scraping {sym} from {start_date} to {end_date}...")
    rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, start_date, end_date)
    if rates is None or len(rates) == 0:
        print(f"Failed to get data for {sym}. Err: {mt5.last_error()}")
        
        # Try alternate symbol name (without 'm')
        alt_sym = sym.replace("m", "")
        print(f"Trying {alt_sym}...")
        rates = mt5.copy_rates_range(alt_sym, mt5.TIMEFRAME_M1, start_date, end_date)
        if rates is None or len(rates) == 0:
            print(f"Failed for {alt_sym} too.")
            continue
        sym = alt_sym

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    out_name = f"{sym}_MT5_1M_2026.parquet"
    out_path = os.path.join(out_dir, out_name)
    df.to_parquet(out_path)
    print(f"Saved {len(df)} rows to {out_path}")

mt5.shutdown()
