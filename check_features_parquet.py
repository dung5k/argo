"""
Tái tạo scaler.pkl đúng cho XAUUSD từ final_features_XAUUSD.parquet
"""
import sys, os, joblib, shutil
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'

print("=== Step 1: Load final_features_XAUUSD.parquet ===")
df = pd.read_parquet(os.path.join(data_dir, 'final_features_XAUUSD.parquet'))
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns[:10])}")

# Remove is_imputed_flag - not scaled
scaleable_cols = [c for c in df.columns if c != 'is_imputed_flag']
print(f"\nScaleable columns ({len(scaleable_cols)}): {scaleable_cols[:10]}")

# Since this is ALREADY scaled data from training, we need the raw version
# Let's check if it looks scaled (mean~0, std~1) or raw
print(f"\nSample stats (should be ~0 mean ~1 std if already scaled):")
print(df[scaleable_cols[:5]].describe().loc[['mean','std']])

print("\n=== Conclusion ===")
print("This file is ALREADY scaled - we cannot refit scaler from it")
print("We need to run feature_engineering.py to get raw features and refit scaler")
print("OR: The scaler needs to match the live data output from create_stationary_features with is_live=True")

# Check what the live FE pipeline produces vs what model expects (from training_metrix)
import json, glob

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_metrix = sorted([m for m in glob.glob(os.path.join(runs_dir, '**', 'training_metrix.json'), recursive=True)
              if 'xauusd' in m.lower()])

print(f"\n=== XAU Training Metrix ===")
for mf in xau_metrix[-2:]:
    with open(mf, encoding='utf-8') as f:
        m = json.load(f)
    feats = m.get('training_metadata', {}).get('data_features', [])
    run_name = os.path.basename(os.path.dirname(mf))
    print(f"\n[{run_name}]: {len(feats)} features")
    if len(feats) > 0:
        print("  First 10:", feats[:10])
        print("  Last 5:", feats[-5:])
        
# Also check final_features vs metrix
print(f"\n=== final_features XAUUSD vs metrix ===")
final_cols = set(scaleable_cols)
if xau_metrix:
    with open(xau_metrix[-1], encoding='utf-8') as f:
        m = json.load(f)
    metrix_feats = set(m.get('training_metadata', {}).get('data_features', []))
    if metrix_feats:
        missing = metrix_feats - final_cols
        extra = final_cols - metrix_feats
        print(f"Features only in metrix (missing from parquet): {list(missing)[:10]}")
        print(f"Features only in parquet (extra vs metrix): {list(extra)[:10]}")
        matching = len(metrix_feats & final_cols)
        print(f"Matching: {matching}/{len(metrix_feats)}")
