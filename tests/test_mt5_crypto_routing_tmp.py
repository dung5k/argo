import os
import sys

safe_script_dir = os.path.dirname(os.path.abspath(__file__))
if safe_script_dir not in sys.path:
    sys.path.insert(0, safe_script_dir)

from src.core.mt5_data_manager import MT5DataManager

def run_test():
    config_path = os.path.join(safe_script_dir, "data", "bot_config_ltc_crypto_v3_5.json")
    print(f"Testing MT5DataManager with config: {config_path}")
    manager = MT5DataManager(log_callback=print, target_sym="LTCUSDT", config_path=config_path)
    
    # Mô phỏng Dynamic Features từ AAMT
    i_feats = [
        "LTCUSDT_close", "LTCUSDT_volume",
        "BTCUSDT_close", "BTCUSDT_volume",
        "ETHUSDT_close",
        "USTEC_close"
    ]
    print("\n[MOCK] Calling force_reload_dynamic_features()...")
    manager.force_reload_dynamic_features(i_feats)
    
    print("\nTesting get_live_merged_data_in_memory(window=5)...")
    merged_df, sym_data, err_msg = manager.get_live_merged_data_in_memory(window=5)
    
    print("\n--- RESULTS ---")
    if err_msg:
        print(f"ERROR: {err_msg}")
    
    if merged_df is not None:
        print(f"Merged DF columns: {merged_df.columns.tolist()}")
        print(f"DataFrame Tail:\n{merged_df.tail(2)}")
    else:
        print("DataFrame is None")
        
    print(f"\nSym Data: {sym_data}")

if __name__ == "__main__":
    run_test()

