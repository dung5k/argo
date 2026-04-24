import sys
import os

_root = os.path.dirname(os.path.abspath('scripts/upload_v3_dataset.py'))
if _root not in sys.path:
    sys.path.insert(0, _root)

from scripts.upload_v3_dataset import filter_by_session
import pandas as pd
import json

raw_dir = 'workspaces/CFG_LTC_ASIAN_V3_5/data/raw'
with open('workspaces/CFG_LTC_ASIAN_V3_5/runs/run_20260423_221500_v3_asian_1/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

fe_cfg = config['FEATURE_ENGINEERING']
all_syms = {config.get('TARGET_SYMBOL', '').upper().replace('M', '')}
all_syms.add(config.get('TARGET_SYMBOL', '').upper())
for sym in fe_cfg.get('MACRO_FEATURES', {}).keys():
    all_syms.add(sym.upper())

df_list = []
for fname in os.listdir(raw_dir):
    if not fname.endswith('.parquet'): continue
    if '_MT5_' in fname:
        sym_raw = fname.split('_MT5_')[0].upper()
    elif '_BINANCE_' in fname:
        sym_raw = fname.split('_BINANCE_')[0].upper()
    else:
        sym_raw = fname.split('_')[0].upper()
    
    matched = any(sym_raw == s.upper() or sym_raw == s.upper().rstrip('M') for s in all_syms)
    if not matched: continue
    
    df_sym = pd.read_parquet(os.path.join(raw_dir, fname))
    rename_map = {c: f"{sym_raw}_{c}" for c in df_sym.columns}
    df_sym = df_sym.rename(columns=rename_map)
    df_list.append(df_sym)

if df_list:
    df_raw = df_list[0].copy()
    for df_next in df_list[1:]:
        df_raw = df_raw.join(df_next, how='outer')
    print("df_raw columns:", df_raw.columns.tolist())
    
    # Try getting XRPUSDT_close
    cols_map = {c.lower(): c for c in df_raw.columns}
    print("XRPUSDT_close in cols_map?", 'xrpusdt_close' in cols_map)
