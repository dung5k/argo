"""
client_master.py - Master Daemon cho Client Machine
====================================================
Cháº¡y liÃªn tá»¥c trÃªn mÃ¡y Client, láº¯ng nghe lá»‡nh tá»« Host thÃ´ng qua
thÆ° má»¥c action_request/ (Ä‘Æ°á»£c Ä‘á»“ng bá»™ qua OneDrive).

Build thÃ nh exe:
    pip install pyinstaller
    pyinstaller --onefile --name master src/client_master.py

CÃ¡ch cháº¡y:
    master.exe --client-id client1 --base-dir "C:\\...\\forex_predictor"
    hoáº·c:
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

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Háº°NG Sá»
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
MASTER_VERSION   = "2.0.0"
POLL_INTERVAL    = 10        # GiÃ¢y: táº§n suáº¥t quÃ©t action_request
HEARTBEAT_EVERY  = 30        # GiÃ¢y: cáº­p nháº­t file heartbeat
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
        
        # Táº¡o thÆ° má»¥c náº¿u chÆ°a cÃ³
        for d in [self.bin_dir, self.req_dir, self.log_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        self.logger = setup_logger(self.log_dir, client_id)
        self.running_process: subprocess.Popen | None = None
        self.current_task_id: str | None = None
        self._stop = False
        
        self.logger.info(f"â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")
        self.logger.info(f"â•‘ CLIENT MASTER v{MASTER_VERSION} - {client_id.upper()}")
        self.logger.info(f"â•‘ Base: {self.base_dir}")
        self.logger.info(f"â•‘ OS  : {platform.system()} {platform.release()}")
        self.logger.info(f"â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•")

    # â”€â”€â”€ Heartbeat â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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

    # â”€â”€â”€ Äá»c vÃ  xá»­ lÃ½ lá»‡nh â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _load_action(self, json_file: Path) -> dict | None:
        try:
            text = json_file.read_text(encoding="utf-8")
            return json.loads(text)
        except Exception as e:
            self.logger.warning(f"KhÃ´ng Ä‘á»c Ä‘Æ°á»£c {json_file.name}: {e}")
            return None

    def _save_action(self, json_file: Path, action: dict):
        try:
            json_file.write_text(json.dumps(action, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self.logger.warning(f"KhÃ´ng ghi Ä‘Æ°á»£c {json_file.name}: {e}")

    def _find_pending_actions(self) -> list[Path]:
        result = []
        for f in sorted(self.req_dir.glob("*.json")):
            action = self._load_action(f)
            if action and action.get("status") == STATUS_PENDING:
                result.append(f)
        return result

    # â”€â”€â”€ Thá»±c thi lá»‡nh â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def _execute(self, json_file: Path, action: dict):
        task_id  = action.get("id", json_file.stem)
        act_type = action.get("type", "EXECUTE").upper()
        
        self.logger.info(f"â–¶ Báº¯t Ä‘áº§u task [{task_id}] type={act_type}")
        
        # Cáº­p nháº­t RUNNING
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
                raise ValueError(f"Loáº¡i lá»‡nh khÃ´ng há»— trá»£: {act_type}")
        except Exception as e:
            self.logger.error(f"âœ— Task [{task_id}] FAILED: {e}")
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
        # Relative â†’ resolve against base_dir
        return str(self.base_dir / p)

    def _do_execute(self, json_file: Path, action: dict):
        task_id  = action["id"]
        command  = action.get("command", "python")
        args     = action.get("args", [])
        cwd_raw  = action.get("cwd", ".")
        env_extra = action.get("env", {})

        # Resolve cwd relative to base_dir náº¿u lÃ  Ä‘Æ°á»ng dáº«n tÆ°Æ¡ng Ä‘á»‘i
        cwd = self._resolve_path(cwd_raw)

        # Resolve command náº¿u lÃ  Ä‘Æ°á»ng dáº«n tÆ°Æ¡ng Ä‘á»‘i (vÃ­ dá»¥: venv/Scripts/python.exe)
        cmd_path = Path(command)
        if not cmd_path.is_absolute() and ('/' in command or '\\' in command):
            command = self._resolve_path(command)

        # Resolve tá»«ng arg lÃ  Ä‘Æ°á»ng dáº«n tÆ°Æ¡ng Ä‘á»‘i
        resolved_args = []
        for a in args:
            a_str = str(a)
            # Náº¿u chá»©a '/' hoáº·c '\' vÃ  khÃ´ng pháº£i path tuyá»‡t Ä‘á»‘i â†’ resolve
            if ('/' in a_str or '\\' in a_str) and not Path(a_str).is_absolute():
                resolved_args.append(self._resolve_path(a_str))
            else:
                resolved_args.append(a_str)

        # Build log file path
        log_file = self.log_dir / f"{task_id}.log"
        # LÆ°u log_file dÆ°á»›i dáº¡ng tÆ°Æ¡ng Ä‘á»‘i so vá»›i base_dir Ä‘á»ƒ cÃ¡c mÃ¡y khÃ¡c xem Ä‘Æ°á»£c
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
        
        status_icon = "âœ“" if exit_code == 0 else "âœ—"
        self.logger.info(f"  {status_icon} Task [{task_id}] xong | exit_code={exit_code}")

    def _do_kill(self, json_file: Path, action: dict):
        task_id = action["id"]
        if self.running_process:
            self.logger.info(f"  âš¡ KILL: Äang dá»«ng process pid={self.running_process.pid}")
            self.running_process.terminate()
            try:
                self.running_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.running_process.kill()
        action["status"]      = STATUS_CANCELLED
        action["finished_at"] = datetime.datetime.now().isoformat()
        self._save_action(json_file, action)
        self.logger.info(f"  âœ“ Kill task [{task_id}] xong")

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
        self.logger.info(f"  âœ“ Status report xong")

    def _do_update_master(self, json_file: Path, action: dict):
        """NÃ¢ng cáº¥p master báº±ng cÃ¡ch cháº¡y file má»›i vÃ  tá»± kill.
        
        Há»— trá»£ cáº£ file .py (python script) vÃ  .exe.
        Host chá»‰ cáº§n copy file má»›i vÃ o bin/ vÃ  gá»­i lá»‡nh UPDATE_MASTER.
        """
        new_file_name = action.get("new_exe", "")  # cÃ³ thá»ƒ lÃ  master_v2.py hoáº·c master_v2.exe
        new_file_path = self.bin_dir / new_file_name

        if not new_file_path.exists():
            raise FileNotFoundError(f"KhÃ´ng tÃ¬m tháº¥y file má»›i: {new_file_path}")

        # Truyá»n láº¡i cÃ¹ng args (--client-id, --base-dir)
        master_args = sys.argv[1:]

        # Chá»n cÃ¡ch cháº¡y dá»±a trÃªn pháº§n má»Ÿ rá»™ng
        suffix = new_file_path.suffix.lower()
        if suffix == ".py":
            launch_cmd = [sys.executable, str(new_file_path)] + master_args
        else:
            # .exe hoáº·c khÃ´ng cÃ³ Ä‘uÃ´i â†’ cháº¡y trá»±c tiáº¿p
            launch_cmd = [str(new_file_path)] + master_args

        self.logger.info(f"  ðŸ”„ UPDATE_MASTER: Khá»Ÿi Ä‘á»™ng [{new_file_name}] rá»“i tá»± táº¯t...")
        self.logger.info(f"     CMD: {' '.join(launch_cmd)}")

        action["status"]      = STATUS_DONE
        action["finished_at"] = datetime.datetime.now().isoformat()
        action["message"]     = f"ÄÃ£ khá»Ÿi Ä‘á»™ng {new_file_name}"
        self._save_action(json_file, action)

        # Khá»Ÿi Ä‘á»™ng master má»›i TRÆ¯á»šC khi tá»± táº¯t
        subprocess.Popen(launch_cmd)
        time.sleep(2)  # Chá» master má»›i á»•n Ä‘á»‹nh
        self._stop = True
        self.logger.info("  ðŸ‘‹ Master cÅ© tá»± táº¯t. ChÃºc master má»›i máº¡nh khoáº»!")
        sys.exit(0)


    # â”€â”€â”€ VÃ²ng láº·p chÃ­nh â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    def run(self):
        # Ghi heartbeat liÃªn tá»¥c trong thread riÃªng
        hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        hb_thread.start()

        def handle_signal(sig, frame):
            self.logger.info("Nháº­n tÃ­n hiá»‡u dá»«ng. Äang táº¯t...")
            self._stop = True

        signal.signal(signal.SIGINT, handle_signal)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, handle_signal)

        self.logger.info(f"ðŸŸ¢ Master Ä‘ang cháº¡y. Poll má»—i {POLL_INTERVAL}s...")
        self.logger.info(f"   Theo dÃµi: {self.req_dir}")

        while not self._stop:
            try:
                pending = self._find_pending_actions()
                if pending:
                    for json_file in pending:
                        if self._stop:
                            break
                        action = self._load_action(json_file)
                        if action and action.get("status") == STATUS_PENDING:
                            # Cháº¡y synchronous (1 task táº¡i 1 thá»i Ä‘iá»ƒm)
                            self._execute(json_file, action)
                else:
                    pass  # KhÃ´ng cÃ³ lá»‡nh má»›i
            except Exception as e:
                self.logger.error(f"Lá»—i vÃ²ng láº·p chÃ­nh: {e}")
            
            time.sleep(POLL_INTERVAL)

        self._write_heartbeat()
        self.logger.info("ðŸ”´ Master Ä‘Ã£ dá»«ng.")


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ENTRY POINT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    parser = argparse.ArgumentParser(description=f"Client Master Daemon v{MASTER_VERSION}")
    parser.add_argument(
        "--client-id", "-c",
        default="client1",
        help="ID cá»§a client (tÃªn thÆ° má»¥c, vÃ­ dá»¥: client1)"
    )
    parser.add_argument(
        "--base-dir", "-b",
        default=str(Path(__file__).resolve().parent.parent),
        help="ÄÆ°á»ng dáº«n gá»‘c cá»§a dá»± Ã¡n (chá»©a data/, runs/, src/, clientN/)"
    )
    args = parser.parse_args()

    master = ClientMaster(
        client_id=args.client_id,
        base_dir=args.base_dir
    )
    master.run()


if __name__ == "__main__":
    main()

