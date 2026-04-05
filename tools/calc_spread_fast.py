import MetaTrader5 as mt5
import pandas as pd
import numpy as np

terminals = {
    "MT5_Chinh": r"C:\Program Files\MetaTrader 5\terminal64.exe",
    "MT5_2": r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe",
    "MT5_EXNESS": r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
}

results = []

# List of highly liquid generic symbols we want to force-check
favorites = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'ETHUSD', 'US30', 'US500', 
             'EURUSDm', 'GBPUSDm', 'USDJPYm', 'XAUUSDm', 'BTCUSDm', 'ETHUSDm', 'US30m', 'US500m',
             'XAGUSD', 'XAGUSDm', 'USOIL', 'USOILm', 'UKOIL', 'UKOILm']

print("Bắt đầu quét Spread các mã phổ biến và trong danh sách theo dõi của bạn...")

for t_name, t_path in terminals.items():
    if not mt5.initialize(path=t_path):
        continue
        
    for fav in favorites:
        mt5.symbol_select(fav, True)
        
    symbols = mt5.symbols_get()
    if not symbols:
        mt5.shutdown()
        continue
    
    # Chỉ lấy những mã ĐANG HIỂN THỊ trong Market Watch hoặc thuộc nhóm Forex Majors/Metals
    filtered_symbols = []
    for s in symbols:
        # Nếu đang hiển thị hoặc là dạng Forex/Metal/Crypto phổ biến
        if s.visible:
            filtered_symbols.append(s)
        
    for s in filtered_symbols:
        rates = mt5.copy_rates_from_pos(s.name, mt5.TIMEFRAME_M5, 0, 288) # 1 days of 5m
        if rates is None or len(rates) < 100:
            continue
            
        df = pd.DataFrame(rates)
        df['height'] = df['high'] - df['low']
        df['spread_price'] = df['spread'] * s.point
        
        valid = df[df['height'] > 0].copy()
        if len(valid) < 50: 
            continue
        
        valid['ratio'] = valid['spread_price'] / valid['height']
        avg_ratio = valid['ratio'].mean() * 100 
        
        results.append({
            'Terminal': t_name,
            'Symbol': s.name,
            'Category': s.path.split('\\')[0] if s.path else 'Unknown',
            'Ratio_%': round(avg_ratio, 2)
        })
        
    mt5.shutdown()

df_res = pd.DataFrame(results)
if not df_res.empty:
    df_res = df_res.sort_values(by='Ratio_%', ascending=True)
    df_res = df_res.drop_duplicates(subset=['Terminal', 'Symbol'])
    df_res.to_csv("all_spreads.csv", index=False)
    
    print("\n" + "="*50)
    print("🏆 TOP 25 MÃ GIAO DỊCH TỐT NHẤT CHO SCALPING M5 (SPREAD CỰC NHỎ)")
    print("="*50)
    print(df_res.head(25).to_string(index=False))
    
    print("\n" + "="*50)
    print("☠️ TOP 15 MÃ LÀ TỬ HUYỆT (CẤM SCALP M5 VÌ SPREAD QUÁ TO)")
    print("="*50)
    if len(df_res) > 25:
        print(df_res.tail(15).to_string(index=False))
else:
    print("Khong co du lieu.")
