import MetaTrader5 as mt5

if not mt5.initialize(r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"):
    print("MT5 EXNESS init failed")
else:
    symbols = mt5.symbols_get()
    matches = [s.name for s in symbols if 'US500' in s.name or 'DXY' in s.name or 'USDIDX' in s.name or 'SPX' in s.name]
    print("Matches:", matches)
    mt5.shutdown()
