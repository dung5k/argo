import sys
def log_callback(msg): print(msg)
from src.core.mt5_data_manager import MT5DataManager
manager = MT5DataManager(log_callback=log_callback, target_sym='XAUUSD')
df, sym_data, err = manager.get_live_merged_data_in_memory(window=5)
print('Error:', err)
print('sym_data:', sym_data)
for col in df.columns:
    if 'close' in col:
        print(f"{col}: {df[col].iloc[-1]}")
