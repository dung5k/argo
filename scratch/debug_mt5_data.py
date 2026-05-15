import json
import pandas as pd
import sys
import os

sys.path.insert(0, r'd:\DungLA\client1')
from src.core.mt5_data_manager import MT5DataManager

with open('bot_config_v6_ltc_weekend.json', 'r') as f:
    config = json.load(f)

manager = MT5DataManager(log_callback=print)
manager.config = config
# Provide lowercase exactly as bot_v6.py receives from column_orders
feats = ['ltcusdt_open', 'ltcusdt_high', 'ltcusdt_low', 'ltcusdt_close', 'ltcusdt_volume', 'ltcusdt_real_volume',
         'btcusdt_open', 'btcusdt_high', 'btcusdt_low', 'btcusdt_close', 'btcusdt_volume', 'btcusdt_real_volume',
         'LTCUSDT_dummy', 'BTCUSDT_dummy']
manager.force_reload_dynamic_features(feats)

df, sym_data, err = manager.get_live_merged_data_in_memory(window=10)
if df is not None:
    print('Merged DF shape:', df.shape)
    print('BTCUSDT cols in df:')
    btc_cols = [c for c in df.columns if 'btcusdt' in c.lower()]
    if btc_cols:
        print(df[btc_cols].tail())
    else:
        print('NO BTCUSDT COLS FOUND!')
else:
    print('Merged DF is None! Err:', err)
