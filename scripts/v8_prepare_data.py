import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone, timedelta
import os

def prepare_v8_data():
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
            
    start_date = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

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
    
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "v8_splits"))
    os.makedirs(out_dir, exist_ok=True)
    
    min_date = df_session.index.min()
    max_date = df_session.index.max()
    
    current_start = min_date
    split_id = 1
    
    print("Generating 4-week Train / 1-week Test splits...")
    while current_start + timedelta(weeks=5) <= max_date:
        train_end = current_start + timedelta(weeks=4)
        test_end = train_end + timedelta(weeks=1)
        
        train_df = df_session[(df_session.index >= current_start) & (df_session.index < train_end)]
        test_df = df_session[(df_session.index >= train_end) & (df_session.index < test_end)]
        
        if len(train_df) > 0 and len(test_df) > 0:
            train_df.to_parquet(os.path.join(out_dir, f"split_{split_id}_train.parquet"))
            test_df.to_parquet(os.path.join(out_dir, f"split_{split_id}_test.parquet"))
            
        current_start += timedelta(weeks=1) # Walk-forward cuộn lên 1 tuần
        split_id += 1
        
    print(f"Generated {split_id-1} splits successfully in {out_dir}")
    mt5.shutdown()

if __name__ == "__main__":
    prepare_v8_data()
