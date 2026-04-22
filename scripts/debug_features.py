import os, sys, json
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
from core.mt5_data_manager import MT5DataManager

def check_features():
    mgr = MT5DataManager(log_callback=print, target_sym="XAUUSD")
    with open('data/bot_config_xau_v1.json') as f:
        mgr.config = json.load(f)
        
    print("SCANNING TERMINALS...")
    mgr.scan_terminals_and_map()
    
    with open('debug_out.txt', 'w', encoding='utf-8') as f:
        f.write("MAPPINGS SUCCESSFUL:\n")
        for k, v in mgr.GLOBAL_MT5_ROUTER_MAP.items():
            f.write(f"  {k} -> {v} (Symbol: {mgr.IN_MEMORY_SYMBOL_HINT.get(k)})\n")
            
        df, _, err = mgr.get_live_merged_data_in_memory(window=10)
        f.write("\nCOLUMNS FETCHED:\n")
        for c in sorted(df.columns):
            f.write(f"  {c}\n")

if __name__ == "__main__":
    check_features()
