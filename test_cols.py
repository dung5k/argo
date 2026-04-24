import pandas as pd
import os

raw_dir = 'workspaces/CFG_LTC_ASIAN_V3_5/data/raw'
all_syms = {'LTCUSDT', 'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'BCHUSDT', 'DOGEUSDT'}
df_list = []
for fname in os.listdir(raw_dir):
    sym_raw = fname.split('_BINANCE_')[0].upper()
    df_sym = pd.read_parquet(os.path.join(raw_dir, fname))
    rename_map = {c: f"{sym_raw}_{c}" for c in df_sym.columns}
    df_sym = df_sym.rename(columns=rename_map)
    df_list.append(df_sym)

df_raw = df_list[0].copy()
for df_next in df_list[1:]:
    df_raw = df_raw.join(df_next, how='outer')

print(df_raw.columns.tolist())
