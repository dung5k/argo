from huggingface_hub import HfApi
import os

token = "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"
repo_id = "dung5k/argo_workspaces"

api = HfApi(token=token)

# Xóa thư mục workspaces trên HF
try:
    print(f"Deleting 'workspaces/' from {repo_id}...")
    api.delete_folder(
        path_in_repo="workspaces",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("Successfully deleted 'workspaces/' from HuggingFace.")
except Exception as e:
    print(f"Error deleting 'workspaces/': {e}")

# Xóa results
try:
    print(f"Deleting 'results/' from {repo_id}...")
    api.delete_folder(
        path_in_repo="results",
        repo_id=repo_id,
        repo_type="dataset"
    )
    print("Successfully deleted 'results/' from HuggingFace.")
except Exception as e:
    print(f"Error deleting 'results/': {e}")
