import MetaTrader5 as mt5

def test_symbols():
    if not mt5.initialize():
        print("MT5 Init failed")
        return
        
    acc_info = mt5.account_info()
    if acc_info is not None:
        print(f"Connected to: {acc_info.company} - {acc_info.server}")
    else:
        print("Not logged in.")

    symbols = mt5.symbols_get()
    if symbols is None:
        print("No symbols")
        return
        
    print(f"Total symbols total: {len(symbols)}")
    mt5.shutdown()

if __name__ == "__main__":
    test_symbols()
