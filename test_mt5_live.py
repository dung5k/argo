import sys
from src.core.mt5_data_manager import MT5DataManager

def run():
    print("Initializing MT5DataManager...")
    manager = MT5DataManager(log_callback=print, target_sym="XAUUSD", config_path="data/bot_config_xau_london_v2.json")
    print("Scanning terminals...")
    manager.scan_terminals_and_map()
    print("Router Map:", manager.GLOBAL_MT5_ROUTER_MAP)
    print("Symbol Hints:", manager.IN_MEMORY_SYMBOL_HINT)
    
    # Try fetching data manually for VIXYm and US_10Y_YIELD
    print("Testing get_live_merged_data_in_memory...")
    df, syms, err = manager.get_live_merged_data_in_memory(window=10)
    print("Final Error:", err)
    if df is not None:
        print("Columns fetched:", list(df.columns))
    else:
        print("DF is NONE!")

if __name__ == "__main__":
    run()
