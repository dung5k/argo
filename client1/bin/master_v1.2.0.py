"""
client_master.py - Master Daemon cho Client Machine v1.2.0
===========================================================
Chạy liên tục trên máy Client, lắng nghe lệnh từ Host thông qua
thư mục action_request/ (được đồng bộ qua OneDrive).

Cách chạy:
    python src/client_master.py --client-id client1 --base-dir "C:\\...\\forex_predictor"

CHANGELOG:
  v1.2.0 - Non-blocking execute: long tasks chạy trong thread riêng
           Log stream qua PIPE thay vì file handle → không lock file
           KILL/STATUS/UPDATE_MASTER nhận được ngay cả khi TRAIN đang chạy
  v1.1.0 - Fix UTF-8 env, relative path, .py self-update
  v1.0.0 - Initial release
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
import platform
import subprocess
import threading
import datetime
from pathlib import Path

# ─────────────────────────────────────────
# HẰNG SỐ
# ─────────────────────────────────────────
MASTER_VERSION   = "1.2.0"
POLL_INTERVAL    = 5         # Giây: tần suất quét action_request (giảm xuống 5s)
HEARTBEAT_EVERY  = 15        # Giây: cập nhật heartbeat thường xuyên hơn
STATUS_PENDING   = "PENDING"
STATUS_RUNNING   = "RUNNING"
STATUS_DONE      = "DONE"
STATUS_FAILED    = "FAILED"
STATUS_CANCELLED = "CANCELLED"

# Loại lệnh ưu tiên cao - nhận ngay cả khi đang BUSY
PRIORITY_TYPES   = {"KILL", "STATUS", "UPDATE_MASTER"}


def setup_logger(log_dir: Path, client_id: str) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"master_{datetime.date.today().isoformat()}.log"

    logger = logging.getLogger("master")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(str(log_file), encoding="utf-8")
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


class ClientMaster:
    def __init__(self, client_id: str, base_dir: str):
        self.client_id  = client_id
        self.base_dir   = Path(base_dir)
        self.client_dir = self.base_dir / client_id
        self.bin_dir    = self.client_dir / "bin"
        self.req_dir    = self.client_dir / "action_request"
        self.log_dir    = self.client_dir / "logs"

        for d in [self.bin_dir, self.req_dir, self.log_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.logger = setup_logger(self.log_dir, client_id)

        # --- State tracking ---
        self.running_process: subprocess.Popen | None = None
        self.current_task_id: str | None = None
        self._task_thread: threading.Thread | None = None   # Thread chạy long task
        self._stop = False
        self._lock = threading.Lock()                        # Protect shared state

        self.logger.info("╔══════════════════════════════════════════")
        self.logger.info(f"║ CLIENT MASTER v{MASTER_VERSION} - {client_id.upper()}")
        self.logger.info(f"║ Base: {self.base_dir}")
        self.logger.info(f"║ OS  : {platform.system()} {platform.release()}")
        self.logger.info("╚══════════════════════════════════════════")

    # ─── Heartbeat ───────────────────────────────────────────────────
    def _is_busy(self) -> bool:
        return (self._task_thread is not None and self._task_thread.is_alive())

    def _write_heartbeat(self):
        hb_file = self.client_dir / "heartbeat.json"
        data = {
            "client_id"   : self.client_id,
            "master_ver"  : MASTER_VERSION,
            "timestamp"   : datetime.datetime.now().isoformat(),
            "status"      : "BUSY" if self._is_busy() else "IDLE",
            "current_task": self.current_task_id,
            "os"          : f"{platform.system()} {platform.release()}"
        }
        try:
            hb_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _heartbeat_loop(self):
        while not self._stop:
            self._write_heartbeat()
            time.sleep(HEARTBEAT_EVERY)

    # ─── Đọc / ghi lệnh ─────────────────────────────────────────────
    def _load_action(self, json_file: Path) -> dict | None:
        try:
            return json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as e:
            self.logger.warning(f"Không đọc được {json_file.name}: {e}")
            return None

    def _save_action(self, json_file: Path, action: dict):
        try:
            json_file.write_text(json.dumps(action, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Không ghi được {json_file.name}: {e}")

    def _find_pending_actions(self) -> list[Path]:
        """Trả về danh sách file lệnh PENDING.

        Khi BUSY:  chỉ trả về lệnh ưu tiên cao (KILL, STATUS, UPDATE_MASTER).
        Khi IDLE:  trả về tất cả.
        """
        busy = self._is_busy()
        result = []
        for f in sorted(self.req_dir.glob("*.json")):
            action = self._load_action(f)
            if not action or action.get("status") != STATUS_PENDING:
                continue
            act_type = action.get("type", "EXECUTE").upper()
            if busy and act_type not in PRIORITY_TYPES:
                continue   # Đang bận → bỏ qua TRAIN/EXECUTE mới
            result.append(f)
        return result

    # ─── Resolve path ────────────────────────────────────────────────
    def _resolve_path(self, path_str: str) -> str:
        p = Path(path_str)
        if p.is_absolute():
            return str(p)
        return str(self.base_dir / p)

    # ─── Dispatch ────────────────────────────────────────────────────
    def _dispatch(self, json_file: Path, action: dict):
        task_id  = action.get("id", json_file.stem)
        act_type = action.get("type", "EXECUTE").upper()

        self.logger.info(f"▶ Bắt đầu task [{task_id}] type={act_type}")
        action["status"]     = STATUS_RUNNING
        action["started_at"] = datetime.datetime.now().isoformat()
        self._save_action(json_file, action)

        try:
            if act_type in ("EXECUTE", "TRAIN", "RUN"):
                # LONG TASK → chạy trong thread riêng, không block master
                self._launch_async(json_file, action)
            elif act_type == "KILL":
                self._do_kill(json_file, action)
            elif act_type == "STATUS":
                self._do_status(json_file, action)
            elif act_type == "UPDATE_MASTER":
                self._do_update_master(json_file, action)
            else:
                raise ValueError(f"Loại lệnh không hỗ trợ: {act_type}")
        except Exception as e:
            self.logger.error(f"✗ Task [{task_id}] FAILED: {e}")
            action["status"]      = STATUS_FAILED
            action["finished_at"] = datetime.datetime.now().isoformat()
            action["error"]       = str(e)
            self._save_action(json_file, action)
            with self._lock:
                if self.current_task_id == task_id:
                    self.current_task_id = None

    # ─── LONG TASK: chạy async trong thread ─────────────────────────
    def _launch_async(self, json_file: Path, action: dict):
        """Khởi động subprocess trong thread riêng → master không bị block."""
        task_id   = action["id"]
        command   = action.get("command", "python")
        args      = action.get("args", [])
        cwd_raw   = action.get("cwd", ".")
        env_extra = action.get("env", {})

        cwd = self._resolve_path(cwd_raw)

        # Resolve command nếu là relative path
        if not Path(command).is_absolute() and ('/' in command or '\\' in command):
            command = self._resolve_path(command)

        # Resolve args
        resolved_args = []
        for a in args:
            a_str = str(a)
            if ('/' in a_str or '\\' in a_str) and not Path(a_str).is_absolute():
                resolved_args.append(self._resolve_path(a_str))
            else:
                resolved_args.append(a_str)

        cmd = [command] + resolved_args

        # Log file path - lưu relative để các máy khác xem được
        log_file = self.log_dir / f"{task_id}.log"
        try:
            action["log_file"] = str(log_file.relative_to(self.base_dir)).replace("\\", "/")
        except ValueError:
            action["log_file"] = str(log_file)
        self._save_action(json_file, action)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"]       = "1"
        env.update(env_extra)

        self.logger.info(f"  CMD: {' '.join(cmd)}")
        self.logger.info(f"  CWD: {cwd}")
        self.logger.info(f"  LOG: {log_file}  [non-blocking, stream qua PIPE]")

        def _thread_body():
            proc = None
            exit_code = -1
            try:
                proc = subprocess.Popen(
                    cmd, cwd=cwd, env=env,
                    # PIPE thay vì file → tránh file lock trên Windows
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                with self._lock:
                    self.running_process = proc
                    self.current_task_id = task_id

                # --- Stream từng dòng vào log file ---
                # Mở append mode với line buffering
                # Python 3.6+ trên Windows mở với FILE_SHARE_READ|WRITE|DELETE
                # → các process khác đọc được trong khi ta đang ghi
                with open(log_file, "w", encoding="utf-8", buffering=1) as lf:
                    lf.write(f"=== Task {task_id} | {datetime.datetime.now().isoformat()} ===\n")
                    lf.write(f"CMD: {' '.join(cmd)}\n\n")
                    lf.flush()

                    for line in proc.stdout:          # đọc từng dòng khi có
                        lf.write(line)
                        lf.flush()                    # flush ngay → có thể đọc realtime

                exit_code = proc.wait()

            except Exception as ex:
                self.logger.error(f"  Thread task [{task_id}] lỗi: {ex}")
                # Ghi lỗi vào log
                try:
                    with open(log_file, "a", encoding="utf-8") as lf:
                        lf.write(f"\n[MASTER ERROR] {ex}\n")
                except Exception:
                    pass
            finally:
                with self._lock:
                    self.running_process = None
                    self.current_task_id = None

                final_status = STATUS_DONE if exit_code == 0 else STATUS_FAILED
                action["status"]      = final_status
                action["exit_code"]   = exit_code
                action["finished_at"] = datetime.datetime.now().isoformat()
                self._save_action(json_file, action)

                icon = "✓" if exit_code == 0 else "✗"
                self.logger.info(f"  {icon} Task [{task_id}] xong | exit_code={exit_code}")

        thread = threading.Thread(target=_thread_body, name=f"task-{task_id}", daemon=True)
        with self._lock:
            self._task_thread = thread
        thread.start()
        # _dispatch() trả về ngay → main loop tiếp tục poll

    # ─── KILL ────────────────────────────────────────────────────────
    def _do_kill(self, json_file: Path, action: dict):
        task_id = action["id"]
        with self._lock:
            proc = self.running_process
            killed_task = self.current_task_id

        if proc:
            self.logger.info(f"  KILL: dừng process pid={proc.pid} (task={killed_task})")
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            self.logger.info(f"  KILL xong.")
        else:
            self.logger.info(f"  KILL: không có process nào đang chạy.")

        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["killed_task"] = killed_task
        self._save_action(json_file, action)

    # ─── STATUS ──────────────────────────────────────────────────────
    def _do_status(self, json_file: Path, action: dict):
        with self._lock:
            busy = self._is_busy()
            task = self.current_task_id
        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["result"] = {
            "master_version": MASTER_VERSION,
            "is_busy"       : busy,
            "current_task"  : task,
            "os"            : f"{platform.system()} {platform.release()}"
        }
        self._save_action(json_file, action)
        self.logger.info(f"  Status: busy={busy}, task={task}")

    # ─── UPDATE MASTER ───────────────────────────────────────────────
    def _do_update_master(self, json_file: Path, action: dict):
        """Nâng cấp bằng cách chạy file .py/.exe mới rồi tự kill."""
        new_file_name = action.get("new_exe", "")
        new_file_path = self.bin_dir / new_file_name

        if not new_file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy: {new_file_path}")

        master_args = sys.argv[1:]
        suffix = new_file_path.suffix.lower()
        launch_cmd = ([sys.executable, str(new_file_path)] + master_args
                      if suffix == ".py" else [str(new_file_path)] + master_args)

        self.logger.info(f"  UPDATE_MASTER: spawn [{new_file_name}] → tự tắt")
        self.logger.info(f"     CMD: {' '.join(launch_cmd)}")

        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["message"]     = f"Đã khởi động {new_file_name}"
        self._save_action(json_file, action)

        subprocess.Popen(launch_cmd)
        time.sleep(2)
        self._stop = True
        self.logger.info("  Master cũ tự tắt.")
        sys.exit(0)

    # ─── Main loop ───────────────────────────────────────────────────
    def run(self):
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        def handle_signal(sig, frame):
            self.logger.info("Nhận tín hiệu dừng...")
            self._stop = True

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_signal)

        self.logger.info(f"Master v{MASTER_VERSION} san sang. Poll moi {POLL_INTERVAL}s...")
        self.logger.info(f"   Theo doi: {self.req_dir}")

        while not self._stop:
            try:
                pending = self._find_pending_actions()
                for json_file in pending:
                    if self._stop:
                        break
                    action = self._load_action(json_file)
                    if action and action.get("status") == STATUS_PENDING:
                        self._dispatch(json_file, action)
            except Exception as e:
                self.logger.error(f"Loi vong lap chinh: {e}")

            time.sleep(POLL_INTERVAL)

        self._write_heartbeat()
        self.logger.info("Master da dung.")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
def main():
    # --- Tự động tìm base_dir ---
    # Nếu file nằm trong */clientX/bin/ thì lên 3 cấp → forex_predictor/
    # Nếu file nằm trong */src/ thì lên 2 cấp → forex_predictor/
    _script = Path(__file__).resolve()
    if _script.parent.name.lower() == "bin":
        _default_base = str(_script.parent.parent.parent)
    else:
        _default_base = str(_script.parent.parent)

    parser = argparse.ArgumentParser(description=f"Client Master Daemon v{MASTER_VERSION}")
    parser.add_argument("--client-id", "-c", default="client1",
                        help="ID của client (tên thư mục, ví dụ: client1)")
    parser.add_argument("--base-dir", "-b",
                        default=_default_base,
                        help="Đường dẫn gốc dự án (chứa data/, runs/, src/, clientN/)")
    args = parser.parse_args()
    ClientMaster(client_id=args.client_id, base_dir=args.base_dir).run()


if __name__ == "__main__":
    main()
