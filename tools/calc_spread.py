import MetaTrader5 as mt5
import pandas as pd
import numpy as np

terminals = {
    "MT5 Chính (1)": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "MT5 - 2": r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
    "MT5 EXNESS": r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
}

bases = ['BTC', 'ETH', 'LTC', 'SOL', 'BNB', 'XRP', 'BCH', 'ADA', 'XAU', 'AVAX']

results = []

for t_name, t_path in terminals.items():
    if not mt5.initialize(path=t_path):
        print(f"Khong the ket noi {t_name}")
        continue
        
    symbols = mt5.symbols_get()
    if not symbols:
        mt5.shutdown()
        continue
        
    for s in symbols:
        name = s.name.upper()
        # Find symbols matching our bases
        is_match = False
        for b in bases:
            if name.startswith(b) and 'USD' in name:
                is_match = True
                break
        
        if not is_match: continue
        
        # Get 5m candles for 2 days (576 candles)
        rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M5, 0, 576)
        if rates is None or len(rates) < 50:
            continue
            
        df = pd.DataFrame(rates)
        
        # Calculate Height
        df['height'] = df['high'] - df['low']
        
        # Calculate Spread in Price using point
        point = s.point
        df['spread_price'] = df['spread'] * point
        
        # Filter zero height
        valid = df[df['height'] > 0].copy()
        if len(valid) == 0: continue
        
        # Calculate Ratio
        valid['ratio'] = valid['spread_price'] / valid['height']
        avg_ratio = valid['ratio'].mean() * 100 # In percentage
        
        # Average points and height just for logging
        avg_spread_pts = valid['spread'].mean()
        avg_height_prc = valid['height'].mean()
        
        results.append({
            'Terminal': t_name,
            'Symbol': s.name,
            'Ratio (%)': avg_ratio,
            'Avg Height': avg_height_prc,
            'Avg Spread (pts)': avg_spread_pts
        })
        
    mt5.shutdown()

# Sort and Group
df_res = pd.DataFrame(results)
if not df_res.empty:
    df_res = df_res.sort_values(by='Ratio (%)', ascending=True)
    print("=== KET QUA (% CHENH LECH SPREAD SO VOI DO CAO NEN 5 PHUT) ===")
    print("Theo thu tu Nho nhat (Tot nhat) -> Lon nhat (Xau nhat):")
    print(df_res.to_string(index=False))
else:
    print("Khong lay duoc du lieu")
