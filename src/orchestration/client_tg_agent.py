"""
client_tg_agent.py - Telegram Agent cho Client Machine v2.0
============================================================
Thay thế cơ chế polling OneDrive bằng Telegram Bot API.
- Cross-network: hoạt động khác mạng hoàn toàn
- Latency: 3-10 giây (đủ dùng cho lệnh TRAIN/KILL)
- Monitor từ điện thoại: gửi lệnh và xem progress ngay trên Telegram
- Zero extra deps: chỉ dùng urllib (stdlib Python)

Cài thư viện: Không cần gì thêm!

Chạy:
    python src/client_tg_agent.py --client-id clientGH --base-dir "C:\\...\\forex_predictor"

Lệnh (gửi từ Telegram):
    /train [client_id] [config]   → Bắt đầu training (config mặc định: xauusd)
    /kill [client_id]             → Dừng training
    /status                       → Xem trạng thái tất cả client
    /log [client_id]              → Xem 20 dòng cuối log

Ví dụ:
    /train clientGH               → train xauusd trên clientGH
    /train clientGH xauusd        → tương tự
    /kill clientGH
    /status
"""

import os
import sys

def ensure_dependencies():
    pass
ensure_dependencies()


import sys
import json
import logging
import argparse
import platform
import datetime
import threading
import subprocess
import time
from pathlib import Path

# Thêm src vào path để import tg_helper và mqtt_helper
_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC))
from tg_helper import TelegramBot
try:
    import hf_sync
except ImportError:
    hf_sync = None
try:
    from mqtt_helper import MqttHelper
except ImportError:
    MqttHelper = None

AGENT_VERSION = "2.2.0-SkyNet"

ARGO_DATA_DIR = os.environ.get("ARGO_DATA_DIR", "C:/argo/data")
os.environ["ARGO_DATA_DIR"] = ARGO_DATA_DIR

ARGO_LOGS_DIR = os.environ.get("ARGO_LOGS_DIR", "C:/argo/logs")
os.environ["ARGO_LOGS_DIR"] = ARGO_LOGS_DIR

CONFIG_MAP = {
    "xauusd": f"{ARGO_DATA_DIR}/bot_config_xau.json",
    "xau"   : f"{ARGO_DATA_DIR}/bot_config_xau.json",
    "xau_v1_5": f"{ARGO_DATA_DIR}/bot_config_xau_v1_5.json",
    "xag_v1_5": f"{ARGO_DATA_DIR}/bot_config_xag_v1_5.json",
    "xau_v2": f"{ARGO_DATA_DIR}/bot_config_xau_ny_v2.json",
    "xau_ny_v2": f"{ARGO_DATA_DIR}/bot_config_xau_ny_v2.json",
    "xag_v2": f"{ARGO_DATA_DIR}/bot_config_xag_v2.json",
    "xau_v2_0": f"{ARGO_DATA_DIR}/bot_config_xau_ny_v2.json",
    "xag_v2_0": f"{ARGO_DATA_DIR}/bot_config_xag_v2.json",
    "xau_v2.0": f"{ARGO_DATA_DIR}/bot_config_xau_ny_v2.json",
    "xag_v2.0": f"{ARGO_DATA_DIR}/bot_config_xag_v2.json",
    "ltc"   : f"{ARGO_DATA_DIR}/bot_config_ltc.json",
    "oil"   : f"{ARGO_DATA_DIR}/bot_config_oil.json",
}


def load_tg_config(base_dir: Path) -> dict:
    path = base_dir / "tg_config.json"
    if not path.exists():
        print(f"[LOI] Khong tim thay {path}")
        print("Hay tao file tg_config.json va dien bot_token + allowed_chat_ids")
        sys.exit(1)
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if "YOUR_BOT_TOKEN" in cfg.get("bot_token", ""):
        print("[LOI] Chua cau hinh bot_token trong tg_config.json!")
        sys.exit(1)
    return cfg


def setup_logger(log_dir: Path, client_id: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tg_agent_{datetime.date.today().isoformat()}.log"
    unified_file = log_dir / f"{client_id}_unified.log"
    logger = logging.getLogger(f"tg_agent_{client_id}")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    
    if not logger.handlers:
        for handler in [logging.FileHandler(str(log_file), encoding="utf-8"),
                        logging.FileHandler(str(unified_file), encoding="utf-8"),
                        logging.StreamHandler(sys.stdout)]:
            handler.setFormatter(fmt)
            logger.addHandler(handler)
    return logger


class TrainingManager:
    """Quản lý subprocess training — thread-safe."""

    def __init__(self, base_dir: Path, client_id: str, logger: logging.Logger, mqtt_helper=None):
        self.base_dir  = base_dir
        self.client_id = client_id
        self.logger    = logger
        self.mqtt_helper = mqtt_helper
        self._lock     = threading.Lock()
        self._proc     = None
        self._task_id  = None
        self._log_file = None
        self._start_time = None
        self._on_done_cb = None  # callback khi training xong

    def _python_exe(self) -> str:
        venv = self.base_dir / "venv" / "Scripts" / "python.exe"
        if venv.exists():
            try:
                r = subprocess.run([str(venv), "-c", "import sys; print(sys.version)"],
                                   capture_output=True, timeout=5)
                if r.returncode == 0:
                    return str(venv)
            except Exception:
                pass
        return sys.executable

    def is_busy(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

    def log_file(self):
        return self._log_file

    def status_text(self) -> str:
        if self.is_busy():
            elapsed = ""
            if self._start_time:
                secs = int((datetime.datetime.now() - self._start_time).total_seconds())
                elapsed = f" | ⏱ {secs//3600:02d}:{(secs%3600)//60:02d}:{secs%60:02d}"
            return f"🔄 BUSY — task: <code>{self._task_id}</code>{elapsed}"
        return "💤 IDLE"

    def start_train(self, config_path: str, code: str = None, script: str = "", config_content: str = "", on_done=None, session: str = "all", **kwargs) -> dict:
        if self.is_busy():
            return {"ok": False, "error": "Đang busy. Gửi /kill trước."}

        task_id  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_train"
        log_dir  = Path(ARGO_LOGS_DIR) / self.client_id
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{task_id}.log"
        
        self.target_name = "XAG" if (config_path and "xag" in config_path.lower()) else "XAU"
        self.version_name = "v1.5" if (config_path and "v1_5" in config_path.lower()) or (script and "v1_5" in script) else "v2"

        python       = self._python_exe()
        
        if code:
            train_script = str(self.base_dir / f"train_temp_{self.client_id}.py")
            with open(train_script, "w", encoding="utf-8") as f:
                f.write(code)
        elif script:
            train_script = str(self.base_dir / script)
        else:
            if config_path and "v1_5" in config_path:
                train_script = str(self.base_dir / "src" / "training_v1_5" / "train_v1_5.py")
            else:
                train_script = str(self.base_dir / "src" / "training_v2" / "train_v2.py")

        cmd = [python, train_script]
        
        if config_path:
            config_abs = (str(self.base_dir / config_path)
                          if not Path(config_path).is_absolute() else config_path)
            
            if config_content:
                Path(config_abs).parent.mkdir(parents=True, exist_ok=True)
                with open(config_abs, "w", encoding="utf-8") as f:
                    f.write(config_content)
                self.logger.info(f"  [CONFIG] Đã tự động tạo/lưu file cấu hình vào: {config_abs}")
                
            if not Path(config_abs).exists() and not code:
                return {"ok": False, "error": f"Không tìm thấy config: {config_abs}"}
            cmd.append(config_abs)

        if session and session.lower() != "all":
            cmd.extend(["--session", session.lower()])

        env = os.environ.copy()
        perf_mode = kwargs.get("perf_mode", "MAX").upper()
        if perf_mode == "LIGHT":
            import multiprocessing
            cores = multiprocessing.cpu_count()
            threads = str(max(1, cores // 2))
            env["OMP_NUM_THREADS"] = threads
            env["OPENBLAS_NUM_THREADS"] = threads
            env["MKL_NUM_THREADS"] = threads
            env["VECLIB_MAXIMUM_THREADS"] = threads
            env["NUMEXPR_NUM_THREADS"] = threads
            env["PERFORMANCE_MODE"] = "LIGHT"
        else:
            env["PERFORMANCE_MODE"] = "MAX"
        env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"})
        # Đảm bảo train_v2.py và hf_sync.pull_data dùng cùng data path
        if os.name == 'nt':
            os.environ["ARGO_DATA_DIR"] = "C:\\argo\\data"
            os.environ["ARGO_LOGS_DIR"] = "C:\\argo\\logs"
            env["ARGO_DATA_DIR"] = "C:\\argo\\data"
            env["ARGO_LOGS_DIR"] = "C:\\argo\\logs"
        else:
            os.environ["ARGO_DATA_DIR"] = str(self.base_dir / "data")
            os.environ["ARGO_LOGS_DIR"] = str(self.base_dir / "logs")
            env["ARGO_DATA_DIR"] = str(self.base_dir / "data")
            env["ARGO_LOGS_DIR"] = str(self.base_dir / "logs")

        self.logger.info(f"▶ START TRAIN task={task_id}")
        self._on_done_cb = on_done

        def _run():

            # ── BƯỚC 1.5: Tải Data Khổng lồ từ HuggingFace (nếu có cấu hình) ──
            if hf_sync:
                try:
                    hf_sync.pull_data(self.logger, config_path=config_abs if config_path else None)
                except Exception as hf_ex:
                    self.logger.warning(f"  [HF] ⚠ Lỗi đồng bộ data từ HF: {hf_ex} (tiếp tục)")

            # ── BƯỚC 2: Chạy training ──
            try:
                proc = subprocess.Popen(
                    cmd, cwd=str(self.base_dir), env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                with self._lock:
                    self._proc       = proc
                    self._task_id    = task_id
                    self._log_file   = log_file
                    self._start_time = datetime.datetime.now()

                unified_log_file = log_dir.parent / f"{self.client_id}_unified.log"
                with open(log_file, "w", encoding="utf-8", buffering=1) as lf, \
                     open(unified_log_file, "a", encoding="utf-8", buffering=1) as uf:
                    lf.write(f"=== Task {task_id} | {datetime.datetime.now().isoformat()} ===\n")
                    lf.write(f"CMD: {' '.join(cmd)}\n\n")
                    for line in proc.stdout:
                        lf.write(line)
                        lf.flush()
                        
                        # Formatting output for unified log with clear timestamp
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        uf.write(f"{ts} [TRAIN] {line}")
                        uf.flush()
                        
                        sys.stdout.write(line)
                        sys.stdout.flush()
                        if self.mqtt_helper:
                            self.mqtt_helper.send_log("TRAIN", line.strip())

                exit_code = proc.wait()
                self.logger.info(f"{'✓' if exit_code == 0 else '✗'} Task {task_id} xong, exit={exit_code}")
                if self._on_done_cb:
                    self._on_done_cb(task_id, exit_code)
            except Exception as ex:
                self.logger.error(f"✗ Task lỗi: {ex}")
                if self.mqtt_helper:
                    self.mqtt_helper.send_log("ERR", f"✗ Task lỗi: {ex}")
            finally:
                with self._lock:
                    self._proc    = None
                    self._task_id = None

        threading.Thread(target=_run, daemon=True, name=f"train-{task_id}").start()
        return {"ok": True, "task_id": task_id, "log_file": str(log_file)}

    def kill(self) -> dict:
        with self._lock:
            proc    = self._proc
            task_id = self._task_id
        if not proc or proc.poll() is not None:
            return {"ok": True, "message": "Không có task nào đang chạy."}
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {"ok": True, "message": f"Đã dừng task <code>{task_id}</code>"}

    def last_log_lines(self, n: int = 20) -> str:
        """Đọc N dòng cuối của log file hiện tại."""
        if not self._log_file or not self._log_file.exists():
            return "(chưa có log)"
        try:
            lines = self._log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            # Lọc các dòng có nội dung quan trọng
            important = [l for l in lines if any(kw in l for kw in
                         ["Epoch", "WR:", "VLoss:", "ĐỈNH", "PHOENIX", "LOI", "Error", "mẫu tốt hơn"])]
            shown = important[-n:] if important else lines[-n:]
            return "\n".join(shown) or "(log trống)"
        except Exception as e:
            return f"(lỗi đọc log: {e})"


class TelegramAgent:
    def __init__(self, client_id: str, base_dir: Path, cfg: dict):
        self.client_id    = client_id
        self.base_dir     = base_dir
        self.cfg          = cfg
        self.bot          = TelegramBot(cfg["bot_token"])
        self.allowed_ids  = set(cfg.get("allowed_chat_ids", []))
        self.poll_sec     = cfg.get("poll_interval_sec", 5)
        self.progress_n   = cfg.get("progress_every_n_epochs", 10)
        self._offset      = 0

        log_dir      = Path(ARGO_LOGS_DIR) / client_id
        self.logger  = setup_logger(log_dir, client_id)

        self.mqtt = MqttHelper(client_id, self._handle_mqtt_cmd) if MqttHelper else None
        if not self.mqtt:
            self.logger.warning("Không tìm thấy MqttHelper. Chạy chế độ Single-mode (Telegram only).")

        self.manager = TrainingManager(base_dir, client_id, self.logger, self.mqtt)
        # Bỏ Ngrok Server vì đã chuyển sang dùng MQTT

    def _handle_mqtt_cmd(self, payload: dict):
        action = payload.get("cmd", "")
        # === LOG MỌI LỆNH NHẬN ĐƯỢC RA CONSOLE CLIENT ===
        code_len = len(payload.get("code", ""))
        if code_len:
            self.logger.info(f"📥 [MQTT CMD] Nhận lệnh: '{action}' | Code payload: {code_len} ký tự")
        else:
            self.logger.info(f"📥 [MQTT CMD] Nhận lệnh: '{action}' | payload={payload}")

        if action == "train":
            symbol = payload.get("symbol", "xauusd").lower()
            script = payload.get("script", "")
            perf_mode = payload.get("perf_mode", "MAX")
            session = payload.get("session", "all")
            config_content = payload.get("config_content", "")
            config = CONFIG_MAP.get(symbol, f"{ARGO_DATA_DIR}/bot_config_{symbol}.json")
            self.logger.info(f"  ➜ Khởi động TRAIN cục bộ, symbol={symbol}, session={session}, script={script}, config={config}, mode={perf_mode}")
            res = self.manager.start_train(config, script=script, config_content=config_content, perf_mode=perf_mode, session=session)
            if not res.get("ok"):
                self.logger.error(f"  [LỖI] Không thể khởi động train: {res.get('error')}")
                if self.mqtt:
                    self.mqtt.send_log("ERR", f"Lỗi khởi động train: {res.get('error')}")
            else:
                if self.mqtt:
                    self.mqtt.send_log("INFO", f"Khởi động train bằng file cục bộ cho {symbol} ({perf_mode} mode)")
                self._notify_all(f"✅ <b>{self.client_id}</b>: Tiến trình Training ({symbol}) đã bắt đầu (MQTT)!\nTask: <code>{res.get('task_id')}</code>")
        elif action == "train_code":
            code = payload.get("code", "")
            if not code: return
            self.logger.info(f"  ➜ [ZERO-GIT] Nhận Nhộng Code ({len(code)} ký tự) — Đang ghi file tạm và khởi chạy Train...")
            res = self.manager.start_train(config_path="", code=code)
            if not res.get("ok"):
                self.logger.error(f"  [LỖI] Không thể khởi động Zero-Git train: {res.get('error')}")
                if self.mqtt:
                    self.mqtt.send_log("ERR", f"Lỗi khởi động Zero-Git train: {res.get('error')}")
            else:
                if self.mqtt:
                    self.mqtt.send_log("INFO", f"Khởi động tiến trình Bơm Code Train trực tiếp (Zero-Git)")
        elif action == "kill":
            self.logger.info("  ➜ Nhận lệnh KILL — Đang dừng tiến trình train...")
            self.manager.kill()
            if self.mqtt:
                self.mqtt.send_log("INFO", "Đã nhận lệnh Kill bằng MQTT")
            self._notify_all(f"🛑 <b>{self.client_id}</b>: Đã dừng tiến trình theo lệnh MQTT!")
        elif action == "run":
            script = payload.get("script", "")
            if not script: return
            self.logger.info(f"  ➜ Nhận lệnh RUN script: {script}")
            def _run_script():
                try:
                    python = self.manager._python_exe()
                    r = subprocess.run([python, str(self.base_dir / script)], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    out = r.stdout.strip() if r.stdout else r.stderr.strip()
                    self.logger.info(f"  [RUN OUT] {script}:\n{out[:500]}")
                    if self.mqtt:
                        self.mqtt.send_log("RUN_OUT", f"[{script}] {out}")
                except Exception as e:
                    self.logger.error(f"  [RUN ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("RUN_ERR", f"Lỗi chạy {script}: {e}")
            threading.Thread(target=_run_script, daemon=True).start()
            
        elif action == "update":
            self.logger.info("  ➜ Nhận lệnh UPDATE (Git Hard Pull)")
            def _git_pull():
                try:
                    self.logger.info("  [GIT] Đang fetch --all và reset --hard origin/main...")
                    if self.mqtt: self.mqtt.send_log("INFO", "Bắt đầu cập nhật mã nguồn (Hard Pull)...")
                    self._notify_all(f"♻️ <b>{self.client_id}</b>: Đang kéo Code mới qua MQTT và tự khởi động lại...")
                    
                    r1 = subprocess.run(["git", "fetch", "--all"], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    r2 = subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    
                    out_msg = (r1.stdout + r2.stdout).strip()
                    self.logger.info(f"  [GIT OUT]:\n{out_msg}")
                    if self.mqtt: self.mqtt.send_log("INFO", f"Git Pull thành công:\n{r2.stdout.strip()}")
                except Exception as e:
                    self.logger.error(f"  [GIT ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("ERR", f"Lỗi cập nhật Git: {e}")
            threading.Thread(target=_git_pull, daemon=True).start()

        elif action == "run_code":
            code = payload.get("code", "")
            if not code: return
            self.logger.info(f"  ➜ [RUN_CODE] Nhận code ({len(code)} ký tự) — Đang thực thi tức thời...")
            def _run_raw():
                try:
                    import tempfile
                    fd, path = tempfile.mkstemp(suffix=".py", text=True)
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        f.write(code)
                    python = self.manager._python_exe()
                    r = subprocess.run([python, path], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    out = r.stdout.strip() if r.stdout else r.stderr.strip()
                    self.logger.info(f"  [RUN_CODE OUT]:\n{out[:1000]}")
                    if self.mqtt:
                        self.mqtt.send_log("RUN_OUT", f"[RAW_CODE] \n{out}")
                    try: os.remove(path)
                    except: pass
                except Exception as e:
                    self.logger.error(f"  [RUN_CODE ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("RUN_ERR", f"Lỗi chạy RAW_CODE: {e}")
            threading.Thread(target=_run_raw, daemon=True).start()

        elif action == "receive_file":
            # Nhận file nhỏ (<= 512KB) gửi thẳng qua MQTT (base64)
            import base64
            dest    = payload.get("dest", "")
            content = payload.get("content_b64", "")
            fname   = payload.get("filename", dest)
            size    = payload.get("size", 0)
            if not dest or not content:
                self.logger.error("  [RECV_FILE] Thiếu dest hoặc content_b64!")
                return
            try:
                if dest.startswith("data/"):
                    dest_path = Path(ARGO_DATA_DIR) / dest[5:]
                else:
                    dest_path = self.base_dir / dest
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                raw_bytes = base64.b64decode(content)
                with open(dest_path, "wb") as f:
                    f.write(raw_bytes)
                msg = f"Đã nhận và lưu file '{fname}' ({size/1024:.1f}KB) → {dest}"
                self.logger.info(f"  [RECV_FILE] {msg}")
                if self.mqtt: self.mqtt.send_log("INFO", msg)
            except Exception as e:
                self.logger.error(f"  [RECV_FILE ERR] {e}")
                if self.mqtt: self.mqtt.send_log("ERR", f"Lỗi lưu file {fname}: {e}")

        elif action == "pull_hf_data":
            # Kéo thư mục data/ từ HuggingFace về
            self.logger.info("  ➜ [PULL_HF_DATA] Đang kéo data từ HuggingFace...")
            def _pull_data():
                try:
                    import sys as _sys
                    _sys.path.insert(0, str(self.base_dir / "src" / "orchestration"))
                    from hf_sync import pull_data
                    ok = pull_data(self.logger)
                    if self.mqtt:
                        self.mqtt.send_log("INFO", "Kéo data từ HF hoàn tất!" if ok else "Kéo data HF thất bại!")
                except Exception as e:
                    self.logger.error(f"  [PULL_HF ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("ERR", f"Lỗi pull_hf_data: {e}")
            threading.Thread(target=_pull_data, daemon=True).start()

        elif action == "pull_hf_file":
            # Kéo 1 file cụ thể từ HuggingFace về
            hf_path   = payload.get("hf_path", "")
            local_dest = payload.get("local_dest", hf_path)
            if not hf_path:
                return
            self.logger.info(f"  ➜ [PULL_HF_FILE] Đang kéo {hf_path} từ HuggingFace...")
            def _pull_file():
                try:
                    import json as _json
                    cfg_path = self.base_dir / "tg_config.json"
                    if not cfg_path.exists():
                        self.logger.error(f"  [PULL_HF_FILE] Không tìm thấy tg_config.json")
                        return
                    cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
                    from huggingface_hub import hf_hub_download
                    local_path = hf_hub_download(
                        repo_id=cfg["hf_repo_id"], repo_type="dataset",
                        token=cfg["hf_token"], filename=hf_path,
                        local_dir=str(self.base_dir)
                    )
                    msg = f"Đã kéo file '{hf_path}' từ HF về '{local_path}'"
                    self.logger.info(f"  [PULL_HF_FILE] {msg}")
                    if self.mqtt: self.mqtt.send_log("INFO", msg)
                except Exception as e:
                    self.logger.error(f"  [PULL_HF_FILE ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("ERR", f"Lỗi pull_hf_file: {e}")
            threading.Thread(target=_pull_file, daemon=True).start()

        elif action == "pull_hf_runs":
            # Kéo thư mục runs/ (trọng số) từ HuggingFace về
            self.logger.info("  ➜ [PULL_HF_RUNS] Đang kéo trọng số từ HuggingFace...")
            t_prefix = payload.get("target_prefix", None)
            c_id = payload.get("config_id", None)
            
            def _pull_runs():
                try:
                    import sys as _sys
                    _sys.path.insert(0, str(self.base_dir / "src" / "orchestration"))
                    from hf_sync import pull_runs
                    ok = pull_runs(self.logger, target_prefix=t_prefix, config_id=c_id)
                    if self.mqtt:
                        self.mqtt.send_log("INFO", "Kéo trọng số từ HF hoàn tất!" if ok else "Kéo trọng số HF thất bại!")
                except Exception as e:
                    self.logger.error(f"  [PULL_HF_RUNS ERR] {e}")
                    if self.mqtt: self.mqtt.send_log("ERR", f"Lỗi pull_hf_runs: {e}")
            threading.Thread(target=_pull_runs, daemon=True).start()

        elif action == "deploy_agent":
            # Yêu cầu cập nhật Hard Reset từ GitHub Toàn Hệ Thống thay vì Base64
            self.logger.info("  [DEPLOY] Thực hiện Hard Reset & Pull Cập Nhật Toàn Bộ Dự Án...")
            if self.mqtt: self.mqtt.send_log("INFO", "Thực hiện Hard Reset & Pull Cập Nhật Toàn Bộ Agent...")
            def _restart():
                try: 
                    subprocess.run(["git", "fetch", "--all"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "reset", "--hard", "origin/main"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "clean", "-fd", "runs/"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "pull", "--rebase"], cwd=str(self.base_dir), timeout=60)
                except: pass
                if self.mqtt: self.mqtt.send_log("INFO", "Git Pull xong! Tự động Restart...")
                time.sleep(2)
                self.manager.kill()
                os._exit(69)
            threading.Thread(target=_restart, daemon=True).start()


        elif action == "update":
            def _do_update():
                time.sleep(2)  # Đợi 2s để vòng lặp chính hồi đáp(ack) tin nhắn cho MQTT/TG
                try: 
                    subprocess.run(["git", "stash"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "clean", "-fd", "runs/"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "pull", "--rebase"], cwd=str(self.base_dir), timeout=60)
                except: pass
                if self.mqtt: self.mqtt.send_log("INFO", "Tự động Khởi động lại theo lệnh Update...")
                self.manager.kill()
                os._exit(69)
            threading.Thread(target=_do_update, daemon=True).start()



    def _send(self, chat_id: int, text: str):
        self.bot.send_message(chat_id, text)

    def _notify_all(self, text: str, photo_path: str = None):
        for cid in self.allowed_ids:
            if photo_path and os.path.exists(photo_path):
                self.bot.send_photo(cid, photo_path, caption=text)
            else:
                self._send(cid, text)

    def _handle_command(self, chat_id: int, text: str):
        parts = text.strip().split()
        if not parts:
            return
        cmd = parts[0].lower().lstrip("/")

        # /status — không cần client_id
        if cmd == "status":
            status = self.manager.status_text()
            self._send(chat_id, f"📊 <b>{self.client_id}</b>\n{status}\n🖥 {platform.system()} {platform.release()}")
            return

        # Các lệnh cần chỉ định client_id
        target = parts[1].lower() if len(parts) > 1 else ""

        # /train [client_id] [symbol] [session]
        if cmd == "train":
            if target and target != self.client_id.lower():
                return  # Lệnh cho client khác, bỏ qua
            symbol = (parts[2] if len(parts) > 2 else "xauusd").lower()
            session_arg = (parts[3] if len(parts) > 3 else "all").lower()
            config = CONFIG_MAP.get(symbol, f"data/bot_config_{symbol}.json")
            self._send(chat_id, f"🔄 <b>{self.client_id}</b>: Đang khởi động training <code>{symbol}</code> (Session: {session_arg})...")

            def on_done(task_id, exit_code):
                icon = "✅" if exit_code == 0 else "❌"
                self._notify_all(f"{icon} <b>{self.client_id}</b>: Training <code>{task_id}</code> xong "
                                 f"(exit={exit_code})")

            result = self.manager.start_train(config, on_done=on_done)
            if result["ok"]:
                self._send(chat_id, f"✅ <b>{self.client_id}</b>: Tiến trình Training ({symbol}) đã bắt đầu!\n"
                                    f"Task: <code>{result['task_id']}</code>")
            else:
                self._send(chat_id, f"❌ <b>{self.client_id}</b>: {result['error']}")

        # /kill [client_id]
        elif cmd == "kill":
            if target and target != self.client_id.lower():
                return
            result = self.manager.kill()
            self._send(chat_id, f"🛑 <b>{self.client_id}</b>: {result['message']}")

        # /log [client_id] [n_lines]
        elif cmd == "log":
            if target and target != self.client_id.lower():
                return
            n = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 20
            log_text = self.manager.last_log_lines(n)
            import html
            self._send(chat_id, f"📋 <b>{self.client_id}</b> — Log gần nhất:\n<pre>{html.escape(log_text[:3000])}</pre>")

        # /run [client_id] [script_path]
        elif cmd == "run":
            if target and target != self.client_id.lower():
                return
            script_path = parts[2] if len(parts) > 2 else ""
            if not script_path:
                self._send(chat_id, "❌ Thiếu tên file. Ví dụ: /run clientGH src/check_gpu.py")
                return

            self._send(chat_id, f"⚙️ <b>{self.client_id}</b>: Đang cập nhật code và thực thi <code>{script_path}</code>...")
            
            def _run_cmd_script():
                try:
                    subprocess.run(["git", "pull", "--rebase"], cwd=str(self.base_dir), capture_output=True, timeout=60)
                except: pass
                
                python = self.manager._python_exe()
                abs_path = self.base_dir / script_path
                if not abs_path.exists():
                    self._send(chat_id, f"❌ <b>{self.client_id}</b>: Không tìm thấy file `{script_path}`")
                    return
                try:
                    r = subprocess.run([python, str(abs_path)], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    out = r.stdout[-3000:] if r.stdout else (r.stderr[-3000:] if r.stderr else "(Không có output)")
                    import html
                    self._send(chat_id, f"✅ <b>{self.client_id}</b> chạy `{script_path}` thành công:\n<pre>{html.escape(out)}</pre>")
                except Exception as e:
                    self._send(chat_id, f"❌ <b>{self.client_id}</b> Lỗi chạy script: {e}")
            
            threading.Thread(target=_run_cmd_script, daemon=True).start()

        # /update [client_id]
        elif cmd == "update":
            if target and target != self.client_id.lower():
                return
            self._send(chat_id, f"♻️ <b>{self.client_id}</b>: Đang kéo Code mới và Tự Khởi Động Lại...")
            def _do_update_tg():
                time.sleep(2)  # Đợi 2s để vòng lặp chính của Telegram kịp đánh dấu(nghiệm thu) msg
                try: 
                    subprocess.run(["git", "stash"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "clean", "-fd", "runs/"], cwd=str(self.base_dir), timeout=20)
                    subprocess.run(["git", "pull", "--rebase"], cwd=str(self.base_dir), timeout=60)
                except: pass
                self.manager.kill()
                os._exit(69)
            threading.Thread(target=_do_update_tg, daemon=True).start()

    def _poll_loop(self):
        self.logger.info("🔄 Đang dọn dẹp các lệnh cũ bị kẹt trong lúc Offline...")
        try:
            old_updates = self.bot.get_updates(offset=self._offset, timeout=0)
            if old_updates:
                self._offset = old_updates[-1]["update_id"] + 1
                self.logger.info(f"🗑 Đã bỏ qua {len(old_updates)} lệnh cũ.")
        except Exception:
            pass

        self.logger.info(f"🔄 Bắt đầu poll Telegram mỗi {self.poll_sec}s (long-poll timeout=30s)")
        while True:
            try:
                updates = self.bot.get_updates(offset=self._offset, timeout=30)
                for upd in updates:
                    self._offset = upd["update_id"] + 1
                    msg = upd.get("message", {})
                    if not msg:
                        continue
                    chat_id = msg.get("chat", {}).get("id")
                    text    = msg.get("text", "")
                    if not text or not chat_id:
                        continue
                    if self.allowed_ids and chat_id not in self.allowed_ids:
                        self.logger.warning(f"Bỏ qua chat_id không được phép: {chat_id}")
                        continue
                    self.logger.info(f"📩 [{chat_id}] {text!r}")
                    if text.startswith("/"):
                        self._handle_command(chat_id, text)
            except Exception as e:
                self.logger.error(f"Poll lỗi: {e}")
                time.sleep(self.poll_sec)

    def _progress_loop(self):
        """Theo dõi log và tự động gửi cập nhật mỗi N epoch HOẶC khi có đỉnh mới."""
        last_sent_epoch = 0
        last_peak_line = ""
        last_heartbeat = 0
        import time
        while True:
            time.sleep(5)  # Poll nhanh hơn để bắt đỉnh mới kịp thời
            
            # --- HEARTBEAT STATUS 30s ---
            now = time.time()
            if now - last_heartbeat > 30:
                last_heartbeat = now
                if getattr(self, "mqtt", None):
                    status = self.manager.status_text()
                    try:
                        import psutil
                        cpu = psutil.cpu_percent()
                        ram = psutil.virtual_memory().percent
                        status += f" | CPU: {cpu}% RAM: {ram}%"
                    except ImportError:
                        pass
                    
                    # Bổ sung Timestamp lần cuối có mặt (Last Seen)
                    import datetime
                    ts = datetime.datetime.now().strftime("%H:%M:%S %d/%m")
                    status += f" | Last Seen: {ts}"
                    
                    self.mqtt.send_log("STATUS", status, retain=True)

            if not self.manager.is_busy():
                last_sent_epoch = 0
                last_peak_line = ""
                continue
            log_file = self.manager.log_file()
            if not log_file or not log_file.exists():
                continue
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                epoch_lines = [l for l in lines if l.startswith("Epoch")]
                last_line = epoch_lines[-1] if epoch_lines else ""
                epoch_num = int(last_line.split()[1]) if last_line and len(last_line.split()) > 1 else 0

                peak_lines = [l for l in lines if "ĐỈNH MỚI" in l or "mẫu tốt hơn" in l]
                current_peak = peak_lines[-1] if peak_lines else ""

                event_lines = [l for l in lines if "[PHOENIX" in l or "Tái sinh!" in l]
                current_event = event_lines[-1] if event_lines else ""

                ver_lines = [l for l in lines if "[VERSION_INFO]" in l]
                current_ver = ver_lines[-1] if ver_lines else ""

                chart_lines = [l for l in lines if "[CHART]" in l]
                current_chart = chart_lines[-1].split("[CHART]")[-1].strip() if chart_lines else None

                git_err_lines = [l for l in lines if "[GIT LỖI PUSH]" in l or "[GIT LỖI THỰC THI THÊM]" in l]
                current_git_err = git_err_lines[-1] if git_err_lines else ""
                
                import html
                send_msg = ""
                
                # Trích xuất version và target từ dòng [RUN] trong logs
                v_name = getattr(self.manager, "version_name", "v?")
                t_name = getattr(self.manager, "target_name", "???")
                run_lines = [l for l in lines if "[RUN]" in l]
                if run_lines:
                    run_name = run_lines[-1].split("[RUN]")[-1].strip()
                    if "v1_5" in run_name.lower(): v_name = "v1.5"
                    elif "v2" in run_name.lower() or "V2" in run_name: v_name = "v2.0"
                    
                    if "CFG_" in run_name:
                        for p in run_name.split("|"):
                            if "CFG_" in p:
                                t_name = p.strip()
                    else:
                        if "xau" in run_name.lower(): t_name = "XAUUSD"
                        elif "xag" in run_name.lower(): t_name = "XAGUSD"

                pfx = f"<b>{self.client_id}</b> [Ver: {v_name} | Mã: {t_name}]"
                
                if current_git_err and current_git_err != getattr(self, "_last_git_err", ""):
                    self._last_git_err = current_git_err
                    send_msg = f"🚨 {pfx} GẶP LỖI ĐẨY GIT!\n"
                    send_msg += f"<pre>{html.escape(current_git_err.strip())}</pre>"
                elif current_ver and current_ver != getattr(self, "_last_ver_info", ""):
                    self._last_ver_info = current_ver
                    send_msg = f"🚀 {pfx} KHỞI ĐỘNG PHIÊN BẢN MỚI!\n"
                    send_msg += f"<pre>{html.escape(current_ver.strip())}</pre>"
                elif current_event and current_event != getattr(self, "_last_tg_event", ""):
                    self._last_tg_event = current_event
                    send_msg = f"🔥 {pfx} PHÁT HIỆN SỰ KIỆN MỚI!\n"
                    if last_line: send_msg += f"<pre>{html.escape(last_line.strip())}</pre>\n"
                    send_msg += f"<pre>{html.escape(current_event.strip())}</pre>"
                elif current_peak and current_peak != last_peak_line:
                    last_peak_line = current_peak
                    send_msg = f"🏆 {pfx} TÌM THẤY MẪU MỚI!\n"
                    if last_line: send_msg += f"<pre>{html.escape(last_line.strip())}</pre>\n"
                    send_msg += f"<pre>{html.escape(current_peak.strip())}</pre>\n"
                    self._notify_all(send_msg, photo_path=current_chart)
                    send_msg = ""  # ? g?i xong nn clear
                elif epoch_num > 0 and epoch_num % self.progress_n == 0 and epoch_num != last_sent_epoch:
                    last_sent_epoch = epoch_num
                    send_msg = f"📈 {pfx} — Tiến độ (Epoch {epoch_num})\n"
                    if last_line: send_msg += f"<pre>{html.escape(last_line.strip())}</pre>"
                    
                if send_msg:
                    self._notify_all(send_msg)
            except Exception as e:
                self.logger.error(f"Progress lỗi: {e}")

    def run(self):
        self.logger.info("╔══════════════════════════════════════════")
        self.logger.info(f"║ TG AGENT v{AGENT_VERSION} — {self.client_id.upper()}")
        self.logger.info(f"║ Base  : {self.base_dir}")
        self.logger.info(f"║ Broker: Telegram Bot API")
        self.logger.info("╚══════════════════════════════════════════")

        # Khởi động kết nối MQTT nếu có
        if self.mqtt:
            self.mqtt.start()

        # Xóa webhook cũ nếu có
        self.bot.delete_webhook()

        # Thông báo online
        self._notify_all(f"🟢 <b>{self.client_id}</b> online! (v{AGENT_VERSION})\n"
                         f"🖥 {platform.system()} {platform.release()}\n"
                         f"📂 {self.base_dir}\n\n"
                         f"Lệnh: /train {self.client_id} | /kill {self.client_id} | /status | /log {self.client_id}")

        # Chạy thread cập nhật tiến độ
        threading.Thread(target=self._progress_loop, daemon=True, name="progress").start()
        
        if self.mqtt:
            self.logger.info("📡 Chế độ Đa Client: Đã TẮT Telegram Long-Polling để tránh đụng độ (HTTP 409).")
            self.logger.info("📡 (Luồng lệnh bây giờ sẽ đi hoàn toàn qua MQTT từ Host Orchestrator).")
            while True:
                time.sleep(1)
        else:
            self.logger.info("🔌 Chạy Độc lập: Bật Telegram Long-Polling (Không có MQTT).")
            self._poll_loop()  # blocking


def main():
    _default_base = str(Path(__file__).resolve().parent.parent)
    parser = argparse.ArgumentParser(description=f"Client Telegram Agent v{AGENT_VERSION}")
    parser.add_argument("--client-id", "-c", default="client1")
    parser.add_argument("--base-dir",  "-b", default=_default_base)
    args = parser.parse_args()

    base_dir = Path(args.base_dir)
    cfg      = load_tg_config(base_dir)
    TelegramAgent(client_id=args.client_id, base_dir=base_dir, cfg=cfg).run()


if __name__ == "__main__":
    main()
