import os
from huggingface_hub import HfApi

hf_token = "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"
api = HfApi(token=hf_token)

latest_run = "run_20260406_145517_xauusd_TRANSFORMER"
local_scaler = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\scaler.pkl"
repo_path = f"runs/{latest_run}/scaler.pkl"

print(f"Uploading {local_scaler} to {repo_path}")
api.upload_file(
    path_or_fileobj=local_scaler,
    path_in_repo=repo_path,
    repo_id="dung5k/argo_data",
    repo_type="dataset",
    commit_message=f"Fix: Overwrite corrupted LTC scaler with correct 100-feature XAU scaler for {latest_run}"
)
print("Upload complete!")
