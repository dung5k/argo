import sys, os, joblib
sys.stdout.reconfigure(encoding='utf-8')

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'
scaler_path = os.path.join(data_dir, 'scaler.pkl')

import os
mtime = os.path.getmtime(scaler_path)
from datetime import datetime
print(f"scaler.pkl last modified: {datetime.fromtimestamp(mtime)}")

scaler = joblib.load(scaler_path)
feats = list(scaler.feature_names_in_)
print(f"Scaler features: {len(feats)}")
print("First 10:", feats[:10])
xau_feats = [f for f in feats if 'XAUUSD' in f]
ltc_feats = [f for f in feats if 'LTC' in f]
print(f"XAUUSD features: {len(xau_feats)} - {xau_feats[:5]}")
print(f"LTC features: {len(ltc_feats)}")
