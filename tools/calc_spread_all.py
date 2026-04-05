import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time

terminals = {
    "MT5_Chinh": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "MT5_2": r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
    "MT5_EXNESS": r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
}

results = []

for t_name, t_path in terminals.items():
    print(f"Connecting to {t_name}...")
    if not mt5.initialize(path=t_path):
        print(f"Failed to connect {t_name}")
        continue
        
    symbols = mt5.symbols_get()
    if not symbols:
        mt5.shutdown()
        continue
        
    print(f"Found {len(symbols)} symbols. Processing...")
    
    count = 0
    for s in symbols:
        count += 1
        if count % 500 == 0:
            print(f"   Processed {count}/{len(symbols)}...")
            
        # Get 5m candles for 2 days (576 candles)
        rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M5, 0, 576)
        if rates is None or len(rates) < 100:
            continue
            
        df = pd.DataFrame(rates)
        
        # Calculate Height
        df['height'] = df['high'] - df['low']
        
        # Calculate Spread in Price using point
        point = s.point
        df['spread_price'] = df['spread'] * point
        
        # Filter zero height
        valid = df[df['height'] > 0].copy()
        if len(valid) < 50: 
            continue
        
        # Calculate Ratio
        valid['ratio'] = valid['spread_price'] / valid['height']
        avg_ratio = valid['ratio'].mean() * 100 # In percentage
        
        avg_spread_pts = valid['spread'].mean()
        avg_height_prc = valid['height'].mean()
        
        results.append({
            'Terminal': t_name,
            'Symbol': s.name,
            'Ratio_%': round(avg_ratio, 2),
            'Avg_Height': avg_height_prc,
            'Avg_Spread_pts': avg_spread_pts
        })
        
    mt5.shutdown()

df_res = pd.DataFrame(results)
if not df_res.empty:
    df_res = df_res.sort_values(by='Ratio_%', ascending=True)
    df_res.to_csv("all_spreads.csv", index=False)
    print(f"Bao cao da duoc luu tai all_spreads.csv voi {len(df_res)} ma giao dich hop le.")
else:
    print("Khong co du lieu.")
