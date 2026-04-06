"""
Kiểm tra end-to-end: mt5_data_manager -> feature_engineering -> tensor shape
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')

def log(msg): print(msg)

from src.core.mt5_data_manager import MT5DataManager
import src.core.feature_engineering as fe
import numpy as np, json

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'

# 1. Pull live data 
manager = MT5DataManager(log_callback=log, target_sym='XAUUSD')
print("\n=== STEP 1: get_live_merged_data_in_memory ===")
merged_df, sym_data, err = manager.get_live_merged_data_in_memory(window=120)

if merged_df is None:
    print("FATAL: merged_df is None!", err)
    sys.exit(1)

print(f"merged_df shape: {merged_df.shape}")
print(f"merged_df columns ({len(merged_df.columns)}): {list(merged_df.columns[:10])}")

# 2. Run feature engineering
print("\n=== STEP 2: create_stationary_features ===")
try:
    df, _ = fe.create_stationary_features(merged_df, is_live=True)
    print(f"df (after fe) shape: {df.shape}")
    print(f"df columns ({len(df.columns)}): {list(df.columns[:10])}")
    print(f"XAUUSD cols: {[c for c in df.columns if 'XAUUSD' in c]}")
except Exception as e:
    import traceback
    print("EXCEPTION in feature_engineering:", e)
    traceback.print_exc()
    sys.exit(1)

# 3. Check scaler expected vs actual
print("\n=== STEP 3: Scaler vs Live feature mismatch check ===")
import pickle, joblib
try:
    scaler = joblib.load(os.path.join(data_dir, 'scaler.pkl'))
    expected = list(scaler.feature_names_in_)
    actual = list(df.columns)
    
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    
    print(f"Scaler expects: {len(expected)} features")
    print(f"FE produces: {len(actual)} features")
    print(f"MISSING from live ({len(missing)}): {missing[:10]}")
    print(f"EXTRA in live ({len(extra)}): {extra[:10]}")
    
    if not missing and not extra:
        print("✅ PERFECT MATCH!")
    else:
        print("❌ MISMATCH!")
except Exception as e:
    print("Scaler load error:", e)

# 4. Check what model expects (from training_metrix)
print("\n=== STEP 4: training_metrix.json model expects ===")
import glob
runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_metrix = [m for m in glob.glob(os.path.join(runs_dir, '**', 'training_metrix.json'), recursive=True)
              if 'xauusd' in m.lower()]
for mf in xau_metrix[-1:]:
    with open(mf) as f:
        m = json.load(f)
    feats = m.get('training_metadata', {}).get('data_features', [])
    print(f"[{os.path.basename(os.path.dirname(mf))}]: {len(feats)} features")

# 5. Check window slicing
print("\n=== STEP 5: Tensor preparation ===")
window_size = 60
last_60_candles = df.iloc[-window_size:].values
print(f"Tensor shape: {last_60_candles.shape}")
print(f"Has NaN: {np.isnan(last_60_candles).any()}")
print(f"Has Inf: {np.isinf(last_60_candles).any()}")
print(f"Expected model input: (1, {window_size}, {last_60_candles.shape[1]})")
