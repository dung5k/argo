import sys
from huggingface_hub import HfApi

token = "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"

print("Đang tải dữ liệu lênt HuggingFace...")
try:
    api = HfApi(token=token)
    api.create_repo(repo_id="dung5k/ltc_v3_tensor_crypto", repo_type="dataset", exist_ok=True, private=True)
    api.upload_folder(
        folder_path="data/CFG_LTC_CRYPTO_V3_5",
        repo_id="dung5k/ltc_v3_tensor_crypto",
        path_in_repo="data/CFG_LTC_CRYPTO_V3_5",
        repo_type="dataset",
        commit_message="Manual push dataset LTC V3"
    )
    print("Upload completed successfully!")
except Exception as e:
    print(f"Lỗi: {e}")
