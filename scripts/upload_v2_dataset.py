import os
import glob
from huggingface_hub import HfApi

# Configuration
hf_token = "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"
repo_id = "dung5k/argo_data"
repo_type = "dataset"
data_dirs = [
    "data/CFG_XAU_LONDON_V2_1",
    "data/CFG_XAU_ASIAN_V2_1",
    "data/CFG_XAU_NY_V2_1"
]

run_id = "V2_2026_DATA"

# Khởi tạo API
api = HfApi(token=hf_token)

print(f"=== BẮT ĐẦU PUSH DỮ LIỆU ĐÀO TẠO ({run_id}) LÊN HUGGING FACE ===")

for data_dir in data_dirs:
    if "LONDON" in data_dir:
        config_id = "CFG_XAU_LONDON_V2_1"
    elif "NY" in data_dir:
        config_id = "CFG_XAU_NY_V2_1"
    else:
        config_id = "CFG_XAU_ASIAN_V2_1"
        
    files_to_upload = [
        f"final_features_{config_id}.parquet",
        f"target_direction_{config_id}.parquet",
        f"scaler_{config_id}.pkl"
    ]
    
    for filename in files_to_upload:
        local_path = os.path.join(data_dir, filename)
        repo_path = f"runs/{run_id}/{filename}"
        
        if not os.path.exists(local_path):
            print(f"⚠️ Không tìm thấy file tại Local: {local_path} -> Bỏ qua!")
            continue
            
        print(f"Uploading {filename} (Size: {os.path.getsize(local_path) / (1024*1024):.2f} MB)...")
        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=repo_id,
                repo_type=repo_type,
                commit_message=f"Sync 10-year MT5 training data ({filename})"
            )
            print(f"✅ Đã Push thành công: {repo_path}")
        except Exception as e:
            print(f"❌ Lỗi khi Push {filename}: {str(e)}")

print("\n🎉 HOÀN TẤT UPLOAD DATASET V2 LÊN ĐÁM MÂY")
