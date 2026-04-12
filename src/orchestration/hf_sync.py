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
        from huggingface_hub.utils import logging as hf_logging
        hf_logging.set_verbosity_error()
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


def push_data(config_path=None):
    """Đẩy các file Data đã qua xử lý (Final Features, Target) lên HuggingFace cụ thể."""
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

    print(f"[HF] Đang đẩy tệp dữ liệu cụ thể lên Đám mây: {repo_id}...")
    api = HfApi()
    
    try:
        api.create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=True, exist_ok=True)
    except: pass

    target_files = []
    
    if config_path:
        # Nếu có chỉ định config_path, TỰ ĐỘNG ĐỌC CONFIG_ID để tìm file!
        import json
        cfg_file_path = Path(config_path)
        if not cfg_file_path.exists():
            cfg_file_path = data_dir / config_path
            
        if cfg_file_path.exists():
            target_files.append(cfg_file_path) # Up cấu hình lên
            try:
                with open(cfg_file_path, "r", encoding="utf-8") as f:
                    bot_cfg = json.load(f)
                    config_id = bot_cfg.get("CONFIG_ID", "")
                    
                    if config_id:
                        f1 = data_dir / f"final_features_{config_id}.parquet"
                        f2 = data_dir / f"target_direction_{config_id}.parquet"
                        f3 = data_dir / f"scaler_{config_id}.pkl"
                        
                        if f1.exists(): target_files.append(f1)
                        if f2.exists(): target_files.append(f2)
                        if f3.exists(): target_files.append(f3)
            except Exception as e:
                print(f"[HF] Lỗi đọc config: {e}")
        else:
            print(f"[HF] Config {config_path} không tồn tại!")
    else:
        # Lọc cụ thể các file cần đẩy thay vì đẩy nguyên folder
        for f in data_dir.glob("*"):
            if f.suffix in [".parquet", ".pkl", ".json"]:
                # Chỉ pick các file config và kết quả feature engineering
                if f.name.startswith("final_features") or f.name.startswith("target_direction") or f.name.startswith("scaler") or f.name.startswith("bot_config"):
                    target_files.append(f)

    if not target_files:
        print("[HF] Không có file cần đẩy (final_features, target, scaler)!")
        return True

    errors = 0
    for f in target_files:
        try:
            print(f"  🚀 Uploading file độc lập: {f.name}")
            api.upload_file(
                path_or_fileobj=str(f),
                path_in_repo=f"data/{f.name}",
                repo_id=repo_id,
                repo_type="dataset",
                token=token,
                commit_message=f"Auto-sync file: {f.name}"
            )
        except Exception as e:
            print(f"[HF] Lỗi khi upload {f.name}: {e}")
            errors += 1

    if errors == 0:
        print("[HF] Đẩy Data thành công lên HuggingFace! 🚀")
        return True
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

def push_runs(logger=None, run_dir=None):
    """Đẩy trọng số lên HuggingFace.
    
    Args:
        run_dir: Nếu chỉ định, chỉ upload file trong thư mục run này (nhanh hơn).
                 Nếu None, upload toàn bộ runs/ (dùng khi sync toàn bộ).
    """
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
    log = logger.info if logger else print

    # Nếu không có run_dir, tìm thư mục được tạo gần nhất trong runs/
    if not run_dir:
        runs_base = Path(argo_logs_dir) / "runs"
        if runs_base.exists():
            subdirs = [d for d in runs_base.iterdir() if d.is_dir() and d.name.startswith("run_")]
            if subdirs:
                latest_run = max(subdirs, key=lambda d: d.stat().st_mtime)
                run_dir = str(latest_run)
                log(f"[HF] Tự động chọn thư mục mới nhất để đẩy: {latest_run.name}")

    if run_dir:
        scan_dir = Path(run_dir)
        base_for_rel = Path(argo_logs_dir)
    else:
        log("[HF] Không tìm thấy thư mục run nào để đẩy.")
        return True

    if not scan_dir.exists():
        return False

    target_files = [
        Path(os.path.join(r, f))
        for r, d, files in os.walk(scan_dir)
        for f in files
        if f.endswith('.pth') or f.endswith('.json') or f.endswith('.pkl') or f.endswith('.png')
    ]

    if not target_files:
        return True

    import time
    api = HfApi()
    try:
        api.create_repo(repo_id=repo_id, token=token, repo_type="dataset", private=True, exist_ok=True)
    except Exception:
        pass

    errors = 0
    for file_path in target_files:
        rel_path = file_path.relative_to(base_for_rel)
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


def pull_runs(logger=None, target_prefix=None, config_id=None):
    """Kéo thư mục runs/ (trọng số) từ HuggingFace về, ưu tiên kéo đúng thư mục cần thiết."""
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

    if target_prefix and config_id:
        pattern = f"runs/*_{target_prefix}_{config_id}_*/**"
        log(f"[HF] Đang kéo trọng số CỤ THỂ ({pattern}) từ {repo_id}/runs/ về...")
    else:
        pattern = "runs/**"
        log(f"[HF] Đang kéo TOÀN BỘ trọng số từ {repo_id}/runs/ về (Cảnh báo: Tốn băng thông!)...")

    try:
        snapshot_download(
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            allow_patterns=pattern,
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
    parser.add_argument("config_path", nargs="?", default=None, help="Đường dẫn đến file cấu hình (cho push data cụ thể)")
    args = parser.parse_args()

    if args.action == "push":
        push_data(config_path=args.config_path)
    elif args.action == "pull":
        pull_data()
    elif args.action == "push_runs":
        push_runs()
    elif args.action == "pull_runs":
        pull_runs()
