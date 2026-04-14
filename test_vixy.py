import sys
from src.core.mt5_data_manager import MT5DataManager

def run():
    manager = MT5DataManager(log_callback=print, target_sym="XAUUSD", config_path="data/bot_config_xau_london_v2.json")
    import MetaTrader5 as mt5
    res = mt5.initialize(path=manager.MT5_PATHS["ICMARKETS"])
    print("Init ICMARKETS:", res)
    # Check if we can find VIX_M25 or VIX_M5 etc.
    syms = mt5.symbols_get()
    vixs = [s.name for s in syms if "VIX" in s.name.upper()]
    print("Available VIX symbols in ICMARKETS:", vixs)
    mt5.shutdown()

if __name__ == "__main__":
    run()
