import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os

def prepare_2026_data():
    mt5_path = "D:/mt5/MetaTrader 5 EXNESS/terminal64.exe"
    print(f"Connecting to MT5: {mt5_path}")
    if not mt5.initialize(mt5_path):
        print("MT5 init failed, error code =", mt5.last_error())
        return

    symbol = "XAUUSDm"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSD"
        if mt5.symbol_info(symbol) is None:
            print("Cannot find XAUUSD or XAUUSDm")
            mt5.shutdown()
            return
            
    start_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2026, 7, 1, tzinfo=timezone.utc) # Grab up to now

    print(f"Scraping {symbol} from {start_date} to {end_date}...")
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start_date, end_date)
    
    if rates is None or len(rates) == 0:
        print(f"Failed to get data for {symbol}. Err: {mt5.last_error()}")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    # Lọc Session: London (khoảng 8:00) đến hết NY (khoảng 22:00)
    df_session = df[(df.index.hour >= 8) & (df.index.hour <= 22)].copy()
    print(f"Total rows after filtering Asian session: {len(df_session)} / {len(df)}")
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(out_dir, exist_ok=True)
    
    out_file = os.path.join(out_dir, "v8_test_2026.parquet")
    df_session.to_parquet(out_file)
            
    print(f"Saved 2026 forward test data to {out_file}")
    mt5.shutdown()

if __name__ == "__main__":
    prepare_2026_data()
