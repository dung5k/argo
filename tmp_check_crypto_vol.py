import MetaTrader5 as mt5
import sys
import pandas as pd
from datetime import datetime

terminals = {
    "DEFAULT": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "EXNESS": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "MTRADING": "C:\\Program Files\\Mtrading MetaTrader 5\\terminal64.exe",
    "MT5_2": "C:\\Program Files\\MetaTrader 5 - 2\\terminal64.exe"
}

symbols_to_check = ['LTCUSD', 'LTCUSDm', 'BTCUSD', 'BTCUSDm', 'ETHUSD', 'ETHUSDm', 'SOLUSD', 'SOLUSDm']

print("=== CHECKING MT5 DATA ===")

for name, path in terminals.items():
    print(f"\n--- Checking {name} ({path}) ---")
    if not mt5.initialize(path=path):
        print(f"X Failed {name} - Code: {mt5.last_error()}")
        continue
        
    for sym in symbols_to_check:
        info = mt5.symbol_info(sym)
        if info is None:
            continue
            
        print(f"  Found: {sym}")
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 5)
        if rates is not None and len(rates) > 0:
            df = pd.DataFrame(rates)
            has_real_volume = df['real_volume'].sum() > 0
            has_tick_volume = df['tick_volume'].sum() > 0
            print(f"    -> real_volume: {'>0' if has_real_volume else '0'} | tick_volume: {'>0' if has_tick_volume else '0'}")
            if has_real_volume:
                print(f"       real vals: {df['real_volume'].tolist()}")
        else:
            print(f"    -> NO DATA")

    mt5.shutdown()
