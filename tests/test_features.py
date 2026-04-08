import pandas as pd
import os
import json
import sys

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'

meta_path = os.path.join(data_dir, 'feature_meta_XAUUSD.json')
with open(meta_path, 'r', encoding='utf-8') as f:
    meta = json.load(f)
print("feature_meta_XAUUSD:", meta)

import glob
runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
metrix_files = glob.glob(os.path.join(runs_dir, '**', 'training_metrix.json'), recursive=True)
for mf in metrix_files:
    print(f"\n[metrix] {os.path.basename(os.path.dirname(mf))}")
    with open(mf, 'r', encoding='utf-8') as f:
        m = json.load(f)
    feats = m.get('training_metadata', {}).get('data_features', [])
    print(f"  total_features: {len(feats)}")
    print(f"  first 10: {feats[:10]}")
    xau_feat = [f for f in feats if 'XAUUSD' in f.upper() or 'XAU_USD' in f.upper()]
    print(f"  xau features ({len(xau_feat)}): {xau_feat}")

# Also check what fe.create_stationary_features returns shape-wise
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')
try:
    import src.core.feature_engineering as fe
    sig = str(fe.create_stationary_features.__doc__ or "no doc")
    print("\nfe.create_stationary_features doc:", sig[:200])
except Exception as e:
    print("fe import error:", e)
