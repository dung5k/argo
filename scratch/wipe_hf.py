import os
from huggingface_hub import HfApi

hf_token = os.environ.get("HF_TOKEN", "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")
api = HfApi()

repo_id = "dung5k/argo_workspaces"
prefix = "workspaces/CFG_LTC_ASIAN_V6"

print(f"Bắt đầu xóa toàn bộ dữ liệu {prefix} trên HuggingFace...")

try:
    files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", token=hf_token)
    to_delete = [f for f in files if f.startswith(prefix)]
    
    if to_delete:
        print(f"Tìm thấy {len(to_delete)} files. Đang tiến hành xóa...")
        # Xóa theo batch để tránh timeout
        batch_size = 50
        for i in range(0, len(to_delete), batch_size):
            batch = to_delete[i:i+batch_size]
            api.delete_files(
                operations=[{"path": path} for path in batch],
                commit_message=f"Delete old brains for {prefix}",
                repo_id=repo_id,
                repo_type="dataset",
                token=hf_token
            )
            print(f"Đã xóa batch {i//batch_size + 1}")
        print("Đã xóa hoàn toàn trên HuggingFace!")
    else:
        print("Không tìm thấy file nào cần xóa trên HuggingFace.")
except Exception as e:
    print(f"Lỗi khi xóa trên HuggingFace: {e}")
