"""
client_master.py - Master Daemon cho Client Machine
====================================================
Chạy liên tục trên máy Client, lắng nghe lệnh từ Host thông qua
thư mục action_request/ (được đồng bộ qua OneDrive).

Build thành exe:
    pip install pyinstaller
    pyinstaller --onefile --name master src/client_master.py

Cách chạy:
    master.exe --client-id client1 --base-dir "C:\\...\\forex_predictor"
    hoặc:
    python src/client_master.py --client-id client1 --base-dir "C:\\...\\forex_predictor"
"""

import os
import sys
import json
import time
import shutil
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
MASTER_VERSION   = "1.1.0"  # Fix UTF-8 env, relative path support, .py self-update
POLL_INTERVAL    = 10        # Giây: tần suất quét action_request
HEARTBEAT_EVERY  = 30        # Giây: cập nhật file heartbeat
STATUS_PENDING   = "PENDING"
STATUS_RUNNING   = "RUNNING"
STATUS_DONE      = "DONE"
STATUS_FAILED    = "FAILED"
STATUS_CANCELLED = "CANCELLED"


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
        
        # Tạo thư mục nếu chưa có
        for d in [self.bin_dir, self.req_dir, self.log_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.logger = setup_logger(self.log_dir, client_id)
        self.running_process: subprocess.Popen | None = None
        self.current_task_id: str | None = None
        self._stop = False
        
        self.logger.info(f"╔══════════════════════════════════════════")
        self.logger.info(f"║ CLIENT MASTER v{MASTER_VERSION} - {client_id.upper()}")
        self.logger.info(f"║ Base: {self.base_dir}")
        self.logger.info(f"║ OS  : {platform.system()} {platform.release()}")
        self.logger.info(f"╚══════════════════════════════════════════")

    # ─── Heartbeat ───────────────────────────────────────────────────
    def _write_heartbeat(self):
        hb_file = self.client_dir / "heartbeat.json"
        data = {
            "client_id"  : self.client_id,
            "master_ver" : MASTER_VERSION,
            "timestamp"  : datetime.datetime.now().isoformat(),
            "status"     : "BUSY" if self.running_process else "IDLE",
            "current_task": self.current_task_id,
            "os"         : f"{platform.system()} {platform.release()}"
        }
        try:
            hb_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _heartbeat_loop(self):
        while not self._stop:
            self._write_heartbeat()
            time.sleep(HEARTBEAT_EVERY)

    # ─── Đọc và xử lý lệnh ──────────────────────────────────────────
    def _load_action(self, json_file: Path) -> dict | None:
        try:
            text = json_file.read_text(encoding="utf-8")
            return json.loads(text)
        except Exception as e:
            self.logger.warning(f"Không đọc được {json_file.name}: {e}")
            return None

    def _save_action(self, json_file: Path, action: dict):
        try:
            json_file.write_text(json.dumps(action, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"Không ghi được {json_file.name}: {e}")

    def _find_pending_actions(self) -> list[Path]:
        result = []
        for f in sorted(self.req_dir.glob("*.json")):
            action = self._load_action(f)
            if action and action.get("status") == STATUS_PENDING:
                result.append(f)
        return result

    # ─── Thực thi lệnh ───────────────────────────────────────────────
    def _execute(self, json_file: Path, action: dict):
        task_id  = action.get("id", json_file.stem)
        act_type = action.get("type", "EXECUTE").upper()
        
        self.logger.info(f"▶ Bắt đầu task [{task_id}] type={act_type}")
        
        # Cập nhật RUNNING
        action["status"]     = STATUS_RUNNING
        action["started_at"] = datetime.datetime.now().isoformat()
        self._save_action(json_file, action)
        self.current_task_id = task_id

        try:
            if act_type == "UPDATE_MASTER":
                self._do_update_master(json_file, action)
            elif act_type == "KILL":
                self._do_kill(json_file, action)
            elif act_type in ("EXECUTE", "TRAIN", "RUN"):
                self._do_execute(json_file, action)
            elif act_type == "STATUS":
                self._do_status(json_file, action)
            else:
                raise ValueError(f"Loại lệnh không hỗ trợ: {act_type}")
        except Exception as e:
            self.logger.error(f"✗ Task [{task_id}] FAILED: {e}")
            action["status"]      = STATUS_FAILED
            action["finished_at"] = datetime.datetime.now().isoformat()
            action["error"]       = str(e)
            self._save_action(json_file, action)
        finally:
            self.current_task_id = None
            self.running_process = None

    def _resolve_path(self, path_str: str) -> str:
        """Resolve relative path against base_dir. Absolute paths stay as-is."""
        p = Path(path_str)
        if p.is_absolute():
            return str(p)
        # Relative → resolve against base_dir
        return str(self.base_dir / p)

    def _do_execute(self, json_file: Path, action: dict):
        task_id  = action["id"]
        command  = action.get("command", "python")
        args     = action.get("args", [])
        cwd_raw  = action.get("cwd", ".")
        env_extra = action.get("env", {})

        # Resolve cwd relative to base_dir nếu là đường dẫn tương đối
        cwd = self._resolve_path(cwd_raw)

        # Resolve command nếu là đường dẫn tương đối (ví dụ: venv/Scripts/python.exe)
        cmd_path = Path(command)
        if not cmd_path.is_absolute() and ('/' in command or '\\' in command):
            command = self._resolve_path(command)

        # Resolve từng arg là đường dẫn tương đối
        resolved_args = []
        for a in args:
            a_str = str(a)
            # Nếu chứa '/' hoặc '\' và không phải path tuyệt đối → resolve
            if ('/' in a_str or '\\' in a_str) and not Path(a_str).is_absolute():
                resolved_args.append(self._resolve_path(a_str))
            else:
                resolved_args.append(a_str)

        # Build log file path
        log_file = self.log_dir / f"{task_id}.log"
        # Lưu log_file dưới dạng tương đối so với base_dir để các máy khác xem được
        try:
            action["log_file"] = str(log_file.relative_to(self.base_dir))
        except ValueError:
            action["log_file"] = str(log_file)
        self._save_action(json_file, action)

        cmd = [command] + resolved_args
        self.logger.info(f"  CMD: {' '.join(cmd)}")
        self.logger.info(f"  CWD: {cwd}")
        self.logger.info(f"  LOG: {log_file}")

        env = os.environ.copy()
        # Bắt buộc UTF-8 để tránh lỗi encode emoji trên Windows
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"]       = "1"
        env.update(env_extra)


        with open(str(log_file), "w", encoding="utf-8") as lf:
            lf.write(f"=== Task {task_id} | {datetime.datetime.now().isoformat()} ===\n")
            lf.write(f"CMD: {' '.join(cmd)}\n\n")
            
            self.running_process = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=lf, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            
            exit_code = self.running_process.wait()

        action["status"]      = STATUS_DONE if exit_code == 0 else STATUS_FAILED
        action["exit_code"]   = exit_code
        action["finished_at"] = datetime.datetime.now().isoformat()
        self._save_action(json_file, action)
        
        status_icon = "✓" if exit_code == 0 else "✗"
        self.logger.info(f"  {status_icon} Task [{task_id}] xong | exit_code={exit_code}")

    def _do_kill(self, json_file: Path, action: dict):
        task_id = action["id"]
        if self.running_process:
            self.logger.info(f"  ⚡ KILL: Đang dừng process pid={self.running_process.pid}")
            self.running_process.terminate()
            try:
                self.running_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.running_process.kill()
        action["status"]      = STATUS_CANCELLED
        action["finished_at"] = datetime.datetime.now().isoformat()
        self._save_action(json_file, action)
        self.logger.info(f"  ✓ Kill task [{task_id}] xong")

    def _do_status(self, json_file: Path, action: dict):
        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["result"] = {
            "master_version" : MASTER_VERSION,
            "is_busy"        : self.running_process is not None,
            "current_task"   : self.current_task_id,
            "os"             : f"{platform.system()} {platform.release()}"
        }
        self._save_action(json_file, action)
        self.logger.info(f"  ✓ Status report xong")

    def _do_update_master(self, json_file: Path, action: dict):
        """Nâng cấp master bằng cách chạy file mới và tự kill.
        
        Hỗ trợ cả file .py (python script) và .exe.
        Host chỉ cần copy file mới vào bin/ và gửi lệnh UPDATE_MASTER.
        """
        new_file_name = action.get("new_exe", "")  # có thể là master_v2.py hoặc master_v2.exe
        new_file_path = self.bin_dir / new_file_name

        if not new_file_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file mới: {new_file_path}")

        # Truyền lại cùng args (--client-id, --base-dir)
        master_args = sys.argv[1:]

        # Chọn cách chạy dựa trên phần mở rộng
        suffix = new_file_path.suffix.lower()
        if suffix == ".py":
            launch_cmd = [sys.executable, str(new_file_path)] + master_args
        else:
            # .exe hoặc không có đuôi → chạy trực tiếp
            launch_cmd = [str(new_file_path)] + master_args

        self.logger.info(f"  🔄 UPDATE_MASTER: Khởi động [{new_file_name}] rồi tự tắt...")
        self.logger.info(f"     CMD: {' '.join(launch_cmd)}")

        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["message"]     = f"Đã khởi động {new_file_name}"
        self._save_action(json_file, action)

        # Khởi động master mới TRƯỚC khi tự tắt
        subprocess.Popen(launch_cmd)
        time.sleep(2)  # Chờ master mới ổn định
        self._stop = True
        self.logger.info("  👋 Master cũ tự tắt. Chúc master mới mạnh khoẻ!")
        sys.exit(0)


    # ─── Vòng lặp chính ─────────────────────────────────────────────
    def run(self):
        # Ghi heartbeat liên tục trong thread riêng
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        def handle_signal(sig, frame):
            self.logger.info("Nhận tín hiệu dừng. Đang tắt...")
            self._stop = True

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, handle_signal)

        self.logger.info(f"🟢 Master đang chạy. Poll mỗi {POLL_INTERVAL}s...")
        self.logger.info(f"   Theo dõi: {self.req_dir}")

        while not self._stop:
            try:
                pending = self._find_pending_actions()
                if pending:
                    for json_file in pending:
                        if self._stop:
                            break
                        action = self._load_action(json_file)
                        if action and action.get("status") == STATUS_PENDING:
                            # Chạy synchronous (1 task tại 1 thời điểm)
                            self._execute(json_file, action)
                else:
                    pass  # Không có lệnh mới
            except Exception as e:
                self.logger.error(f"Lỗi vòng lặp chính: {e}")
            
            time.sleep(POLL_INTERVAL)

        self._write_heartbeat()
        self.logger.info("🔴 Master đã dừng.")


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description=f"Client Master Daemon v{MASTER_VERSION}")
    parser.add_argument(
        "--client-id", "-c",
        default="client1",
        help="ID của client (tên thư mục, ví dụ: client1)"
    )
    parser.add_argument(
        "--base-dir", "-b",
        default=str(Path(__file__).resolve().parent.parent),
        help="Đường dẫn gốc của dự án (chứa data/, runs/, src/, clientN/)"
    )
    args = parser.parse_args()

    master = ClientMaster(
        client_id=args.client_id,
        base_dir=args.base_dir
    )
    master.run()


if __name__ == "__main__":
    main()
