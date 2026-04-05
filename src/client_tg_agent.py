"""
client_tg_agent.py - Telegram Agent cho Client Machine v1.0
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

AGENT_VERSION = "1.2.0-Dual"
CONFIG_MAP = {
    "xauusd": "data/bot_config_xau.json",
    "xau"   : "data/bot_config_xau.json",
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
    logger = logging.getLogger("tg_agent")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    for h in [logging.FileHandler(str(log_file), encoding="utf-8"),
              logging.StreamHandler(sys.stdout)]:
        h.setFormatter(fmt)
        logger.addHandler(h)
    return logger


class TrainingManager:
    """Quản lý subprocess training — thread-safe."""

    def __init__(self, base_dir: Path, client_id: str, logger: logging.Logger, mqtt_helper=None):
        self.base_dir  = base_dir
        self.client_id = client_id
        self.logger    = logger
        self.mqtt_helper = mqtt_helper
        self._lock     = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._task_id: str | None = None
        self._log_file: Path | None = None
        self._start_time: datetime.datetime | None = None
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

    def log_file(self) -> Path | None:
        return self._log_file

    def status_text(self) -> str:
        if self.is_busy():
            elapsed = ""
            if self._start_time:
                secs = int((datetime.datetime.now() - self._start_time).total_seconds())
                elapsed = f" | ⏱ {secs//3600:02d}:{(secs%3600)//60:02d}:{secs%60:02d}"
            return f"🔄 BUSY — task: <code>{self._task_id}</code>{elapsed}"
        return "💤 IDLE"

    def start_train(self, config_path: str, on_done=None) -> dict:
        if self.is_busy():
            return {"ok": False, "error": "Đang busy. Gửi /kill trước."}

        task_id  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_train"
        log_dir  = self.base_dir / self.client_id / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{task_id}.log"

        python       = self._python_exe()
        train_script = str(self.base_dir / "src" / "train_unified.py")
        config_abs   = (str(self.base_dir / config_path)
                        if not Path(config_path).is_absolute() else config_path)

        if not Path(config_abs).exists():
            return {"ok": False, "error": f"Không tìm thấy config: {config_abs}"}

        cmd = [python, train_script, config_abs]
        env = os.environ.copy()
        env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"})

        self.logger.info(f"▶ START TRAIN task={task_id}")
        self._on_done_cb = on_done

        def _run():
            # ── BƯỚC 1: git pull để lấy code và data mới nhất ──
            try:
                self.logger.info("  [GIT] Đang git pull --rebase ...")
                r = subprocess.run(
                    ["git", "pull", "--rebase"],
                    cwd=str(self.base_dir), capture_output=True,
                    text=True, encoding="utf-8", timeout=120
                )
                if r.returncode == 0:
                    self.logger.info(f"  [GIT] ✓ {r.stdout.strip() or 'Already up to date.'}")
                else:
                    self.logger.warning(f"  [GIT] ⚠ git pull thất bại (tiếp tục): {r.stderr.strip()}")
            except Exception as git_ex:
                self.logger.warning(f"  [GIT] ⚠ Không thể git pull: {git_ex} (tiếp tục)")

            # ── BƯỚC 1.5: Tải Data Khổng lồ từ HuggingFace (nếu có cấu hình) ──
            if hf_sync:
                try:
                    hf_sync.pull_data(self.logger)
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

                with open(log_file, "w", encoding="utf-8", buffering=1) as lf:
                    lf.write(f"=== Task {task_id} | {datetime.datetime.now().isoformat()} ===\n")
                    lf.write(f"CMD: {' '.join(cmd)}\n\n")
                    for line in proc.stdout:
                        lf.write(line)
                        lf.flush()
                        if self.mqtt_helper:
                            self.mqtt_helper.send_log("TRAIN", line.strip())

                exit_code = proc.wait()
                self.logger.info(f"{'✓' if exit_code == 0 else '✗'} Task {task_id} xong, exit={exit_code}")
                if self._on_done_cb:
                    self._on_done_cb(task_id, exit_code)
            except Exception as ex:
                self.logger.error(f"✗ Task lỗi: {ex}")
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
                         ["Epoch", "WR:", "VLoss:", "ĐỈNH", "PHOENIX", "LOI", "Error"])]
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

        log_dir      = base_dir / client_id / "logs"
        self.logger  = setup_logger(log_dir, client_id)

        self.mqtt = MqttHelper(client_id, self._handle_mqtt_cmd) if MqttHelper else None
        if not self.mqtt:
            self.logger.warning("Không tìm thấy MqttHelper. Chạy chế độ Single-mode (Telegram only).")

        self.manager = TrainingManager(base_dir, client_id, self.logger, self.mqtt)

    def _handle_mqtt_cmd(self, payload: dict):
        action = payload.get("cmd", "")
        if action == "train":
            symbol = payload.get("symbol", "xauusd")
            config = CONFIG_MAP.get(symbol, f"data/bot_config_{symbol}.json")
            self.manager.start_train(config)
            if self.mqtt:
                self.mqtt.send_log("INFO", f"Khởi động train bằng MQTT cho {symbol}")
        elif action == "kill":
            self.manager.kill()
            if self.mqtt:
                self.mqtt.send_log("INFO", "Đã nhận lệnh Kill bằng MQTT")
        elif action == "run":
            script = payload.get("script", "")
            if not script: return
            def _run_script():
                try:
                    subprocess.run(["git", "pull", "--rebase"], cwd=str(self.base_dir), capture_output=True, timeout=60)
                    python = self.manager._python_exe()
                    r = subprocess.run([python, str(self.base_dir / script)], cwd=str(self.base_dir), capture_output=True, text=True, timeout=60)
                    if self.mqtt:
                        out = r.stdout.strip() if r.stdout else r.stderr.strip()
                        self.mqtt.send_log("RUN_OUT", f"[{script}] {out}")
                except Exception as e:
                    if self.mqtt: self.mqtt.send_log("RUN_ERR", f"Lỗi chạy {script}: {e}")
            threading.Thread(target=_run_script, daemon=True).start()

    def _send(self, chat_id: int, text: str):
        self.bot.send_message(chat_id, text)

    def _notify_all(self, text: str):
        for cid in self.allowed_ids:
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

        # /train [client_id] [symbol]
        if cmd == "train":
            if target and target != self.client_id.lower():
                return  # Lệnh cho client khác, bỏ qua
            symbol = (parts[2] if len(parts) > 2 else "xauusd").lower()
            config = CONFIG_MAP.get(symbol, f"data/bot_config_{symbol}.json")
            self._send(chat_id, f"⏳ <b>{self.client_id}</b>: Đang khởi động training <code>{symbol}</code>...")

            def on_done(task_id, exit_code):
                icon = "✅" if exit_code == 0 else "❌"
                self._notify_all(f"{icon} <b>{self.client_id}</b>: Training <code>{task_id}</code> xong "
                                 f"(exit={exit_code})")

            result = self.manager.start_train(config, on_done=on_done)
            if result["ok"]:
                self._send(chat_id, f"✅ <b>{self.client_id}</b>: Training bắt đầu!\n"
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
            self._send(chat_id, f"📋 <b>{self.client_id}</b> — Log gần nhất:\n<pre>{log_text[:3000]}</pre>")

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
                    self._send(chat_id, f"✅ <b>{self.client_id}</b> chạy `{script_path}` thành công:\n<pre>{out}</pre>")
                except Exception as e:
                    self._send(chat_id, f"❌ <b>{self.client_id}</b> Lỗi chạy script: {e}")
            
            threading.Thread(target=_run_cmd_script, daemon=True).start()

    def _poll_loop(self):
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
        """Theo dõi log và tự động gửi cập nhật mỗi N epoch."""
        last_sent_epoch = 0
        while True:
            time.sleep(15)
            if not self.manager.is_busy():
                last_sent_epoch = 0
                continue
            log_file = self.manager.log_file()
            if not log_file or not log_file.exists():
                continue
            try:
                lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
                epoch_lines = [l for l in lines if l.startswith("Epoch")]
                if not epoch_lines:
                    continue
                last_line = epoch_lines[-1]
                epoch_num = int(last_line.split()[1]) if len(last_line.split()) > 1 else 0
                if epoch_num > 0 and epoch_num % self.progress_n == 0 and epoch_num != last_sent_epoch:
                    last_sent_epoch = epoch_num
                    # Tìm dòng ĐỈNH MỚI gần nhất
                    peak_lines = [l for l in lines if "ĐỈNH MỚI" in l]
                    peak = peak_lines[-1] if peak_lines else ""
                    msg = (f"📈 <b>{self.client_id}</b> — Epoch {epoch_num}\n"
                           f"<pre>{last_line.strip()}</pre>")
                    if peak:
                        msg += f"\n🏆 <pre>{peak.strip()}</pre>"
                    self._notify_all(msg)
            except Exception:
                pass

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
        self._notify_all(f"🟢 <b>{self.client_id}</b> online!\n"
                         f"🖥 {platform.system()} {platform.release()}\n"
                         f"📂 {self.base_dir}\n\n"
                         f"Lệnh: /train {self.client_id} | /kill {self.client_id} | /status | /log {self.client_id}")

        # Chạy 2 thread song song
        threading.Thread(target=self._progress_loop, daemon=True, name="progress").start()
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
