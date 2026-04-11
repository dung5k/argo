import os
import json
import logging
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download
try:
    from huggingface_hub.utils import disable_progress_bars as _hf_disable_progress
except ImportError:
    _hf_disable_progress = None


def _suppress_hf_progress():
    """Tắt progress bar % của huggingface_hub (do tqdm sinh ra trong stdout/stderr)."""
    try:
        if _hf_disable_progress:
            _hf_disable_progress()
    except Exception:
        pass

def _load_config():
    # hf_sync.py = src/orchestration/hf_sync.py
    # parent       = src/orchestration/
    # parent.parent= src/
    # parent.parent.parent = project_root/
    base_dir = Path(__file__).resolve().parent.parent.parent
    config_file = base_dir / "tg_config.json"
    if not config_file.exists():
        return None
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _project_root():
    return Path(__file__).resolve().parent.parent.parent


def push_data():
    """Đẩy toàn bộ thư mục data/ lên HuggingFace bằng cờ HF Token"""
    _suppress_hf_progress()
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        print("[HF] Lỗi: Chưa cấu hình 'hf_token' và 'hf_repo_id' trong tg_config.json")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    argo_data_dir = os.environ.get("ARGO_DATA_DIR", str(_project_root() / "data"))
    data_dir = Path(argo_data_dir)
    
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
            commit_message="Auto-sync data from Host",
            delete_patterns="*",
            ignore_patterns=["*.json"]
        )
        print("[HF] Đẩy Data thành công lên HuggingFace! 🚀")
        return True
    except Exception as e:
        print(f"[HF] Lỗi khi đẩy lên HF: {e}")
        return False

def pull_data(logger: logging.Logger = None, config_path: str = None):
    """Kéo thư mục data/ mới nhất từ HuggingFace về (an toàn, không dùng snapshot_download)."""
    _suppress_hf_progress()
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        msg = "Chưa cấu hình 'hf_token' và 'hf_repo_id' trong tg_config.json. Bỏ qua kéo Data HF."
        if logger: logger.warning(f"[HF] {msg}")
        else: print(f"[HF] {msg}")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    base_dir = _project_root()
    argo_data_dir = os.environ.get("ARGO_DATA_DIR", str(base_dir / "data"))
    data_dir = Path(argo_data_dir)
    
    # Read OPTIONAL REQUIRED PARQUETS list from config
    required_parquets = None
    if config_path:
        import json
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                bot_cfg = json.load(cf)
                required_parquets = bot_cfg.get("HF_CLOUD", {}).get("REQUIRED_PARQUETS", None)
        except Exception as e:
            pass
            
    log = logger.info if logger else print
    log(f"[HF] Bắt đầu tải Parquet data từ {repo_id} (Safe HTTP Method)...")
    
    try:
        from huggingface_hub import HfApi, hf_hub_download
        
        # --- [CLEANUP] Dọn rác các file Parquet/Pkl cũ không còn nằm trong REQUIRED_PARQUETS ---
        if required_parquets and data_dir.exists():
            for local_file in data_dir.glob("*"):
                if local_file.suffix in [".parquet", ".pkl"]:
                    if local_file.name not in required_parquets:
                        try:
                            local_file.unlink()
                            log(f"  🗑️ Đã dọn dẹp file tàn dư: {local_file.name}")
                        except: pass
                        
        api = HfApi()
        files = api.list_repo_files(repo_id=repo_id, repo_type="dataset", token=token)
        parquet_files = [f for f in files if f.startswith("data/") and (f.endswith(".parquet") or f.endswith(".pkl"))]
        if required_parquets:
            parquet_files = [f for f in parquet_files if f.replace("data/", "") in required_parquets]
            log(f"       => Đã lọc {len(parquet_files)}/{len(required_parquets)} file từ cấu hình")
        
        target_dir = str(data_dir.parent)
        for f in parquet_files:
            log(f"  + Checking/Downloading: {f} -> {target_dir}")
            hf_hub_download(
                repo_id=repo_id,
                filename=f,
                repo_type="dataset",
                token=token,
                local_dir=target_dir,
                local_dir_use_symlinks=False
            )
            
        log("[HF] Tải Dữ Liệu Hoàn Tất! Sẵn sàng huấn luyện. ✅")
        return True
    except Exception as e:
        if logger: logger.error(f"[HF] Lỗi khi kéo Data: {e}")
        else: print(f"[HF] Lỗi khi kéo Data: {e}")
        return False

def push_runs(logger=None):
    """Đẩy toàn bộ thư mục runs/ (trọng số) lên HuggingFace"""
    _suppress_hf_progress()
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        msg = "Chưa cấu hình hf_token/hf_repo_id. Bỏ qua push runs."
        if logger: logger.warning(f"[HF] {msg}")
        else: print(f"[HF] {msg}")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    argo_logs_dir = os.environ.get("ARGO_LOGS_DIR", str(_project_root() / "logs"))
    runs_dir = Path(argo_logs_dir) / "runs"
    log = logger.info if logger else print

    if not runs_dir.exists():
        print(f"[HF] Không tìm thấy thư mục {runs_dir}")
        return False

    # Chỉ upload từng file riêng lẻ, không dùng upload_folder để tránh cảnh báo "large folder"
    pth_files = [
        Path(os.path.join(r, f))
        for r, d, files in os.walk(runs_dir)
        for f in files
        if f.endswith('.pth') or f.endswith('.json') or f.endswith('.pkl') or f.endswith('.png')
    ]

    if not pth_files:
        return True

    import time
    api = HfApi()
    try:
        api.create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=True, exist_ok=True)
    except Exception:
        pass

    errors = 0
    for file_path in pth_files:
        rel_path = file_path.relative_to(Path(argo_logs_dir))
        path_in_repo = str(rel_path).replace("\\", "/")
        for attempt in range(3):
            try:
                api.upload_file(
                    path_or_fileobj=str(file_path),
                    path_in_repo=path_in_repo,
                    repo_id=repo_id,
                    repo_type="dataset",
                    token=token,
                    commit_message=f"Auto-sync: {file_path.name}",
                )
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(5)
                else:
                    log(f"[HF] Lỗi upload {file_path.name}: {e}")
                    errors += 1
    return errors == 0


def pull_runs(logger=None):
    """Kéo thư mục runs/ (trọng số) mới nhất từ HuggingFace về"""
    _suppress_hf_progress()
    cfg = _load_config()
    if not cfg or "hf_token" not in cfg or "hf_repo_id" not in cfg:
        msg = "Chưa cấu hình hf_token/hf_repo_id. Bỏ qua pull runs."
        if logger: logger.warning(f"[HF] {msg}")
        else: print(f"[HF] {msg}")
        return False

    token = cfg["hf_token"]
    repo_id = cfg["hf_repo_id"]
    argo_logs_dir = os.environ.get("ARGO_LOGS_DIR", str(_project_root() / "logs"))
    log = logger.info if logger else print
    log(f"[HF] Đang kéo trọng số từ {repo_id}/runs/ về...")

    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            allow_patterns="runs/**",
            local_dir=str(argo_logs_dir),
            local_dir_use_symlinks=False,
            force_download=False
        )
        log("[HF] Kéo trọng số hoàn tất! Sẵn sàng kế thừa. ✅")
        return True
    except Exception as e:
        if logger: logger.error(f"[HF] Lỗi khi kéo runs: {e}")
        else: print(f"[HF] Lỗi khi kéo runs: {e}")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser("HuggingFace Data Sync")
    parser.add_argument("action", choices=["push", "pull", "push_runs", "pull_runs"])
    args = parser.parse_args()

    if args.action == "push":
        push_data()
    elif args.action == "pull":
        pull_data()
    elif args.action == "push_runs":
        push_runs()
    elif args.action == "pull_runs":
        pull_runs()
