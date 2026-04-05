import os
import json
import logging
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

def _load_config():
    base_dir = Path(__file__).resolve().parent.parent
    config_file = base_dir / "tg_config.json"
    if not config_file.exists():
        return None
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except Exception:
        return None

def push_data():
    """Đẩy toàn bộ thư mục data/ lên HuggingFace bằng cờ HF Token"""
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        print("[HF] Lỗi: Chưa cấu hình 'hf_token' và 'hf_repo_id' trong tg_config.json")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    if not data_dir.exists():
        print(f"[HF] Lỗi: Không tìm thấy thư mục {data_dir}")
        return False

    print(f"[HF] Đang đồng bộ Dữ Liệu lên Đám mây: {repo_id}...")
    api = HfApi()
    
    # Tạo repo nếu chưa có
    try:
        api.create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=True, exist_ok=True)
    except Exception as e:
        print(f"[HF] Cảnh báo tạo repo: {e}")

    # Đẩy lên bằng upload_folder (siêu tốc, hỗ trợ ghi đè file cũ)
    try:
        api.upload_folder(
            folder_path=str(data_dir),
            path_in_repo="data",
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            commit_message="Auto-sync data from Host"
        )
        print("[HF] Đẩy Data thành công lên HuggingFace! 🚀")
        return True
    except Exception as e:
        print(f"[HF] Lỗi khi đẩy lên HF: {e}")
        return False

def pull_data(logger: logging.Logger = None):
    """Kéo thư mục data/ mới nhất từ HuggingFace về"""
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        msg = "Chưa cấu hình 'hf_token' và 'hf_repo_id' trong tg_config.json. Bỏ qua kéo Data HF."
        if logger: logger.warning(f"[HF] {msg}")
        else: print(f"[HF] {msg}")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    log = logger.info if logger else print
    log(f"[HF] Bắt đầu tải Parquet data từ {repo_id}...")
    
    try:
        # snapshot_download là siêu cấp thông minh, nó tải về cache sau đó tạo Symlink (hoặc copy) ra ngoài, chỉ tải file nào thay đổi!
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            allow_patterns="data/*",
            local_dir=str(base_dir), # Nó sẽ map thẳng vào thư mục data/
            local_dir_use_symlinks=False, # Tránh lỗi symlink trên Windows
            force_download=False
        )
        log("[HF] Tải Dữ Liệu Hoàn Tất! Sẵn sàng huấn luyện. ✅")
        return True
    except Exception as e:
        if logger: logger.error(f"[HF] Lỗi khi kéo Data: {e}")
        else: print(f"[HF] Lỗi khi kéo Data: {e}")
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("HuggingFace Data Sync")
    parser.add_argument("action", choices=["push", "pull"])
    args = parser.parse_args()
    
    if args.action == "push":
        push_data()
    elif args.action == "pull":
        pull_data()
