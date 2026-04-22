import os
import time
from huggingface_hub import HfApi, snapshot_download

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

REPO_ID = "dung5k/argo_workspaces"
LOCAL_DIR = "workspaces"

# Cấm đồng bộ dữ liệu siêu nặng (Được kế thừa từ STORAGE_POLICY)
IGNORE_RULES = [
    "*/data/raw/*", 
    "*/data/tensors/*",
    "*.parquet",
    "*.npy"
]

import argparse

def pull_workspace(config_id):
    token = os.environ.get("HF_TOKEN", "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")
    if not token:
        log("❌ Lỗi: Không tìm thấy Token HF.")
        return

    log(f"⬇️ ĐANG KÉO (PULL) DATA CHO CẤU HÌNH: {config_id} TỪ MÂY XUỐNG...")
    try:
        ignore_pull = IGNORE_RULES + ["*.log"]
        snapshot_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            local_dir=".",
            allow_patterns=[f"workspaces/{config_id}/*"],
            local_dir_use_symlinks=False,  
            ignore_patterns=ignore_pull,
            token=token,
            max_workers=4
        )
        log("✔️ Kéo (Pull) tài nguyên hoàn tất!")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PULL: {e}")

def push_workspace(config_id):
    token = os.environ.get("HF_TOKEN", "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")
    if not token:
        log("❌ Lỗi: Không tìm thấy Token HF.")
        return

    log(f"⬆️ ĐANG TẢI (PUSH) KẾT QUẢ CỦA CẤU HÌNH: {config_id} LÊN MÂY...")
    try:
        api = HfApi(token=token)
        # Đẩy folder con workspaces/{config_id} lên repo ở đúng đường dẫn đó
        api.upload_folder(
            folder_path=f"workspaces/{config_id}",
            repo_id=REPO_ID,
            path_in_repo=f"workspaces/{config_id}",
            repo_type="dataset",
            ignore_patterns=IGNORE_RULES,
            commit_message=f"Smart Sync: Tự động tải lên các thay đổi mới nhất cho {config_id}",
            run_as_future=False
        )
        log("✔️ Tải lên (Push) HF hoàn tất!")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PUSH: {e}")

def main():
    parser = argparse.ArgumentParser(description="Công cụ Đồng bộ Smart Sync 2 chiều cho Argo")
    parser.add_argument("action", choices=["pull", "push"], help="Hành động cần thực hiện")
    parser.add_argument("config_id", help="Tên cấu hình (VD: CFG_LTC_NY_V3_5)")
    args = parser.parse_args()

    log("="*50)
    log("🚀 KHỞI ĐỘNG CÔNG CỤ ĐỒNG BỘ THÔNG MINH (SMART SYNC)")
    log("="*50)

    if args.action == "pull":
        pull_workspace(args.config_id)
    elif args.action == "push":
        push_workspace(args.config_id)

    log("="*50)
    log("🎉 HOÀN TẤT ĐỒNG BỘ.")
    log("="*50)

if __name__ == "__main__":
    main()

