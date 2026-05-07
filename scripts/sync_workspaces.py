import os
import time
from huggingface_hub import HfApi, snapshot_download

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        # Fallback for Windows console with limited encoding
        clean_msg = str(msg).encode("ascii", errors="replace").decode("ascii")
        print(f"[{time.strftime('%H:%M:%S')}] {clean_msg}", flush=True)

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

    log(f"PULL DATA FOR CONFIG: {config_id} FROM CLOUD...")
    try:
        ignore_pull = IGNORE_RULES + ["*.log"]
        snapshot_download(
            repo_id=REPO_ID,
            repo_type="dataset",
            local_dir=".",
            allow_patterns=[f"workspaces/{config_id}/**"],
            local_dir_use_symlinks=False,  
            ignore_patterns=ignore_pull,
            token=token,
            max_workers=4
        )
        log("✔️ Kéo (Pull) tài nguyên hoàn tất!")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PULL: {e}")

def push_workspace(config_id):
    """Push toàn bộ thư mục config (legacy, ít dùng)."""
    token = os.environ.get("HF_TOKEN", "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")
    if not token:
        log("❌ Lỗi: Không tìm thấy Token HF.")
        return

    log(f"PUSH ALL CONFIG: {config_id} TO CLOUD...")
    try:
        api = HfApi(token=token)
        api.upload_folder(
            folder_path=f"workspaces/{config_id}",
            repo_id=REPO_ID,
            path_in_repo=f"workspaces/{config_id}",
            repo_type="dataset",
            ignore_patterns=IGNORE_RULES,
            commit_message=f"Smart Sync: Push config {config_id}",
            run_as_future=False
        )
        log("✔️ Tải lên (Push) HF hoàn tất!")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PUSH: {e}")

def push_run(config_id, run_id):
    """
    Chỉ đẩy đúng thư mục của lượt chạy hiện tại:
      Local: workspaces/{config_id}/runs/{run_id}/
      HF:    workspaces/{config_id}/runs/{run_id}/
    HuggingFace upload_folder tự so sánh hash, chỉ tốn băng thông
    cho file mới hoặc bị thay đổi. Không hiển thị progress log.
    """
    token = os.environ.get("HF_TOKEN", "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")
    if not token:
        log("❌ Lỗi: Không tìm thấy Token HF.")
        return

    # Tắt hoàn toàn progress bar và verbose log của HF
    try:
        from huggingface_hub.utils import logging as hf_logging, disable_progress_bars
        hf_logging.set_verbosity_error()
        disable_progress_bars()
    except Exception:
        pass

    local_path = f"workspaces/{config_id}/runs/{run_id}"
    hf_path    = f"workspaces/{config_id}/runs/{run_id}"

    if not os.path.isdir(local_path):
        log(f"❌ Không tìm thấy thư mục local: {local_path}")
        return

    log(f"PUSH RUN: {run_id} -> HF (new/changed files only)...")
    try:
        api = HfApi(token=token)
        api.upload_folder(
            folder_path=local_path,
            repo_id=REPO_ID,
            path_in_repo=hf_path,
            repo_type="dataset",
            ignore_patterns=IGNORE_RULES,
            commit_message=f"Best model: {config_id}/{run_id}",
            run_as_future=False
        )
        log(f"✔️ Push run {run_id} hoàn tất!")
    except Exception as e:
        log(f"❌ Lỗi nghiêm trọng lúc PUSH RUN: {e}")

def main():
    parser = argparse.ArgumentParser(description="Công cụ Đồng bộ Smart Sync 2 chiều cho Argo")
    parser.add_argument("action", choices=["pull", "push"], help="Hành động cần thực hiện")
    parser.add_argument("config_id", help="Tên cấu hình (VD: CFG_LTC_NY_V3_5)")
    args = parser.parse_args()

    log("="*50)
    log("[START] KHOI DONG CONG CU DONG BO THONG MINH (SMART SYNC)")
    log("="*50)

    if args.action == "pull":
        pull_workspace(args.config_id)
    elif args.action == "push":
        push_workspace(args.config_id)

    log("="*50)
    log("[DONE] HOAN TAT DONG BO.")
    log("="*50)

if __name__ == "__main__":
    main()

