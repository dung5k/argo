from huggingface_hub import HfApi
import os

token = os.environ.get("HF_TOKEN", "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")
api = HfApi(token=token)

config_id = "CFG_LTC_ASIAN_V6"
run_id = "run_20260514_055620_v6_ASIAN_5m_W12_TP35_SL15_HolyGrail_26"
local_path = f"workspaces/{config_id}/runs/{run_id}"
hf_path = f"workspaces/{config_id}/runs/{run_id}"

IGNORE_RULES = [
    "*/data/raw/*", 
    "*/data/tensors/*",
    "*.parquet",
    "*.npy"
]

print(f"Pushing {local_path} to {hf_path}...")
api.upload_folder(
    folder_path=local_path,
    repo_id="dung5k/argo_workspaces",
    path_in_repo=hf_path,
    repo_type="dataset",
    ignore_patterns=IGNORE_RULES,
    commit_message=f"Deploy best Asian model: {run_id}",
    run_as_future=False
)
print("Push complete.")
