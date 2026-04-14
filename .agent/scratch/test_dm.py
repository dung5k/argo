from src.core.mt5_data_manager import MT5DataManager
import os

print("--- Testing Asian Config ---")
dm1 = MT5DataManager(config_path="data/bot_config_xau_asian_v2_1.json")
df1, sym1, err1 = dm1.get_live_merged_data_in_memory(window=10)
if df1 is not None:
    print(f"Data columns: {list(df1.columns)}")
    print(f"US10Y in df1? {any('UST10Y' in c or 'US_10Y_YIELD' in c or 'ZN' in c for c in df1.columns)}")
    print(f"VIX in df1? {any('VIX' in c for c in df1.columns)}")
else:
    print("Error:", err1)

print("\n--- Testing NY Config ---")
dm2 = MT5DataManager(config_path="data/bot_config_xau_ny_v2_1.json")
df2, sym2, err2 = dm2.get_live_merged_data_in_memory(window=10)
if df2 is not None:
    print(f"Data columns: {list(df2.columns)}")
    print(f"US10Y in df2? {any('UST10Y' in c or 'US_10Y_YIELD' in c for c in df2.columns)}")
    print(f"VIX in df2? {any('VIX' in c for c in df2.columns)}")
else:
    print("Error:", err2)
