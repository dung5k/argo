import sys
from src.core.mt5_data_manager import MT5DataManager

def run():
    manager = MT5DataManager(log_callback=print, target_sym="XAUUSD", config_path="data/bot_config_xau_london_v2.json")
    print("VIXYm in ROUTING:", "VIXYm" in manager.config.get("DATA_SOURCE", {}).get("ROUTING", {}))
    continuous_config = manager.config.get("DATA_SOURCE", {}).get("CONTINUOUS_CONTRACTS", {}).get("VIXYm")
    print("continuous_config:", continuous_config)
    if continuous_config:
        active_contract = manager.get_front_month_contract(continuous_config)
        print("get_front_month_contract:", active_contract)
        
    print("Scanning...")
    manager.scan_terminals_and_map()
    print("VIXYm in ROUTER MAP:", "VIXYm" in manager.GLOBAL_MT5_ROUTER_MAP)
    
if __name__ == "__main__":
    run()
