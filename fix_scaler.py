"""
Script khẩn cấp: Tải đúng scaler.pkl của XAUUSD từ HF về ghi đè local
"""
import os, shutil, json, sys

hf_token = "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"
data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'

from huggingface_hub import HfApi, hf_hub_download
api = HfApi(token=hf_token)

files = list(api.list_repo_files("dung5k/argo_data", repo_type="dataset"))
xau_runs = [f.split('/')[1] for f in files 
            if f.startswith('runs/') and '_xauusd_' in f and 'scaler.pkl' in f]

print("XAU runs with scaler.pkl:", xau_runs)
if not xau_runs:
    print("FATAL: No XAU runs found!")
    sys.exit(1)

latest = max(xau_runs)
print(f"Using run: {latest}")

# Download scaler
scaler_path = hf_hub_download(
    repo_id="dung5k/argo_data", repo_type="dataset", token=hf_token,
    filename=f"runs/{latest}/scaler.pkl"
)

# Backup old
old_scaler = os.path.join(data_dir, 'scaler.pkl')
if os.path.exists(old_scaler):
    shutil.copy(old_scaler, old_scaler + '.bak_ltc')
    print(f"Backed up old scaler to {old_scaler}.bak_ltc")

shutil.copy(scaler_path, old_scaler)
print(f"Copied new XAU scaler from {scaler_path}")

# Verify
import joblib
scaler = joblib.load(old_scaler)
feats = list(scaler.feature_names_in_)
print(f"\nNew scaler has {len(feats)} features")
print("First 10:", feats[:10])
xau_feats = [f for f in feats if 'XAUUSD' in f.upper() or 'XAU_USD' in f.upper()]
print(f"XAUUSD features ({len(xau_feats)}): {xau_feats[:5]}")
print("is_imputed_flag in scaler:", 'is_imputed_flag' in feats)
