import MetaTrader5 as mt5

if not mt5.initialize(r'D:\mt5\MetaTrader 5 EXNESS\terminal64.exe'):
    print("initialize() failed, error code =", mt5.last_error())
    quit()

symbols = mt5.symbols_get()
if symbols is None:
    print("symbols_get() failed, error code =", mt5.last_error())
else:
    print("Total symbols:", len(symbols))
    for s in symbols:
        if 'XAG' in s.name or 'XAU' in s.name or 'US' in s.name or 'DXY' in s.name:
            print(s.name)

mt5.shutdown()
