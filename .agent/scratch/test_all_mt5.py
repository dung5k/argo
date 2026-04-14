import MetaTrader5 as mt5

def check_term(name, path, search_strs):
    print(f"\n--- Checking {name} : {path} ---")
    if not mt5.initialize(path=path):
        print(f"Init failed. Error: {mt5.last_error()}")
        return

    acc_info = mt5.account_info()
    if acc_info is not None:
        print(f"Connected to: {acc_info.company} - {acc_info.server}")
    else:
        print("Not logged in.")

    syms = mt5.symbols_get()
    if syms:
        print(f"Total symbols: {len(syms)}")
        for s in syms:
            s_name = s.name.lower()
            if any(key in s_name for key in search_strs):
                print(f" Found: {s.name}")
    else:
        print("No symbols fetched.")
        
    mt5.shutdown()

if __name__ == "__main__":
    check_term("DEFAULT", r"C:\Program Files\MetaTrader 5\terminal64.exe", ["vix", "us10", "10y", "z10"])
    check_term("MT5_2", r"C:\Program Files\MetaTrader 5 - 2\terminal64.exe", ["vix", "us10", "10y", "z10"])
    check_term("ICMARKETS", r"C:\Program Files\MetaTrader 5 - ICMarkets\terminal64.exe", ["vix", "us10", "10y", "z10"])
