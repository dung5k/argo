import os
from huggingface_hub import HfApi

hf_token = os.environ.get("HF_TOKEN", "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")
api = HfApi(token=hf_token)
repo_id = "dung5k/argo_workspaces"

# Xóa các thư mục LTC V6 trên HuggingFace
for cfg in ["CFG_LTC_NY_V6", "CFG_LTC_ASIAN_V6", "CFG_LTC_LONDON_V6"]:
    try:
        api.delete_folder(path_in_repo=f"workspaces/{cfg}/runs", repo_id=repo_id, repo_type="dataset")
        print(f"Deleted dataset {cfg}")
    except Exception as e:
        print(f"Skipped dataset {cfg}")
        
    try:
        api.delete_folder(path_in_repo=f"workspaces/{cfg}/runs", repo_id=repo_id, repo_type="model")
        print(f"Deleted model {cfg}")
    except Exception as e:
        print(f"Skipped model {cfg}")

print("Cleaned up HF")
