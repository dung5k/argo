"""
host_orchestrator.py - Host Controller (chạy trên máy Host/Antigravity)
=========================================================================
Giao tiếp với Client qua:
  1. HTTP trực tiếp (uu tiên) — latency < 1s, yêu cầu cùng LAN
  2. OneDrive (fallback) — latency 1-5 phút nhưng hoạt động mọi nơi

Dùng:
    from host_orchestrator import HostOrchestrator
    host = HostOrchestrator()
    host.send_train(client_id="client1", config="workspaces/CFG_XAU_NY_V3_5/base_config.json")
"""

import os
import json
import shutil
import datetime
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


BASE_DIR = Path(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor")


class HostOrchestrator:
    def __init__(self, base_dir: str = str(BASE_DIR)):
        self.base_dir = Path(base_dir)

    # ─── HTTP direct communication ────────────────────────────────────
    def _load_registry(self) -> dict:
        """Lấy IP/port của các client từ client_registry.json."""
        reg_path = self.base_dir / "client_registry.json"
        if not reg_path.exists():
            return {}
        try:
            data = json.loads(reg_path.read_text(encoding="utf-8"))
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception:
            return {}

    def _http_post(self, client_id: str, endpoint: str, payload: dict, timeout: int = 5) -> Optional[dict]:
        """Gọi HTTP POST đến client. Trả None nếu thất bại."""
        registry = self._load_registry()
        info = registry.get(client_id, {})
        host = info.get("http_host", "")
        port = info.get("http_port", 7878)
        if not host:
            return None
        url = f"http://{host}:{port}{endpoint}"
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req  = urllib.request.Request(url, data=body,
                                          headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return None

    def _http_get(self, client_id: str, endpoint: str, timeout: int = 3) -> Optional[dict]:
        """Gọi HTTP GET đến client. Trả None nếu thất bại."""
        registry = self._load_registry()
        info = registry.get(client_id, {})
        host = info.get("http_host", "")
        port = info.get("http_port", 7878)
        if not host:
            return None
        url = f"http://{host}:{port}{endpoint}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def _client_dir(self, client_id: str) -> Path:
        return self.base_dir / client_id

    def _req_dir(self, client_id: str) -> Path:
        d = self._client_dir(client_id) / "action_request"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _bin_dir(self, client_id: str) -> Path:
        d = self._client_dir(client_id) / "bin"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ─── Tạo Task ID ─────────────────────────────────────────────────
    def _make_task_id(self, prefix: str = "task") -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{prefix}"   # VD: 20260403_235833_train.json


    # ─── Ghi file lệnh ──────────────────────────────────────────────
    def _write_action(self, client_id: str, action: dict) -> Path:
        task_id = action["id"]
        json_file = self._req_dir(client_id) / f"{task_id}.json"
        json_file.write_text(json.dumps(action, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[HOST] ✓ Gửi lệnh [{task_id}] → {client_id}")
        print(f"       File: {json_file}")
        return json_file

    # ─── DEPLOY TOOL ──────────────────────────────────────────────────
    def _make_relative(self, path: str) -> str:
        """Convert absolute path to relative so it works on any machine."""
        try:
            return str(Path(path).relative_to(self.base_dir)).replace('\\', '/')
        except ValueError:
            return path  # Nếu không thể make relative thì giữ ngúyên

    def deploy_tool(self, client_id: str, source_path: str, dest_name: str = None) -> str:
        """Copy file (script/exe) vào thư mục bin/ của client."""
        src = Path(source_path)
        if not src.exists():
            raise FileNotFoundError(f"Không tìm thấy: {src}")
        dest_name = dest_name or src.name
        dest = self._bin_dir(client_id) / dest_name
        shutil.copy2(str(src), str(dest))
        print(f"[HOST] 📦 Deploy {src.name} → {client_id}/bin/{dest_name}")
        return str(dest)

    # ─── SEND COMMANDS ────────────────────────────────────────────────
    def send_execute(self, client_id: str, command: str, args: list,
                     cwd: str = ".", env: dict = None, task_id: str = None) -> str:
        """Gửi lệnh chạy chương trình bất kỳ.
        
        cwd, args: dùng đường dẫn tương đối để chạy được trên mọi máy.
        """
        task_id = task_id or self._make_task_id("exec")
        action = {
            "id"        : task_id,
            "type"      : "EXECUTE",
            "created_at": datetime.datetime.now().isoformat(),
            "status"    : "PENDING",
            "command"   : command,
            "args"      : args,
            "cwd"       : cwd,   # relative ok, client tự resolve
            "env"       : env or {},
            "started_at": None,
            "finished_at": None,
            "exit_code" : None,
            "log_file"  : None
        }
        self._write_action(client_id, action)
        return task_id

    def send_train(self, client_id: str, config_path: str,
                   python_exe: str = "venv/Scripts/python.exe", task_id: str = None) -> str:
        """Gửi lệnh training với file config JSON.
        
        config_path: Đường dẫn tương đối tới config (ví dụ: workspaces/CFG_XAU_NY_V3_5/base_config.json)
        python_exe : Đường dẫn tương đối tới Python executable
        """
        task_id = task_id or self._make_task_id("train")
        # Dùng path tương đối → Client tự resolve theo base_dir của mình
        train_script = "src/training_v2/train_v2.py"
        # config_path: client gọi sẽ resolve, đảm bảo là relative
        config_rel = self._make_relative(config_path) if Path(config_path).is_absolute() else config_path
        action = {
            "id"        : task_id,
            "type"      : "TRAIN",
            "created_at": datetime.datetime.now().isoformat(),
            "status"    : "PENDING",
            "command"   : python_exe,       # relative: venv/Scripts/python.exe
            "args"      : [train_script, config_rel],  # relative paths
            "cwd"       : "src",            # relative: src/ folder
            "env"       : {},
            "config"    : config_rel,
            "started_at": None,
            "finished_at": None,
            "exit_code" : None,
            "log_file"  : None
        }
        self._write_action(client_id, action)
        return task_id

    def send_kill(self, client_id: str) -> str:
        """Gửi lệnh dừng task đang chạy."""
        task_id = self._make_task_id("kill")
        action = {
            "id"        : task_id,
            "type"      : "KILL",
            "created_at": datetime.datetime.now().isoformat(),
            "status"    : "PENDING"
        }
        self._write_action(client_id, action)
        return task_id

    def send_update_master(self, client_id: str, new_exe_name: str) -> str:
        """Gửi lệnh cập nhật master exe."""
        task_id = self._make_task_id("update")
        action = {
            "id"        : task_id,
            "type"      : "UPDATE_MASTER",
            "created_at": datetime.datetime.now().isoformat(),
            "status"    : "PENDING",
            "new_exe"   : new_exe_name
        }
        self._write_action(client_id, action)
        return task_id

    def send_status_check(self, client_id: str) -> str:
        """Yêu cầu client báo cáo trạng thái."""
        task_id = self._make_task_id("status")
        action = {
            "id"        : task_id,
            "type"      : "STATUS",
            "created_at": datetime.datetime.now().isoformat(),
            "status"    : "PENDING"
        }
        self._write_action(client_id, action)
        return task_id

    # ─── WATCH STATUS ─────────────────────────────────────────────────
    def get_task_status(self, client_id: str, task_id: str) -> dict:
        """Đọc trạng thái của 1 task."""
        json_file = self._req_dir(client_id) / f"{task_id}.json"
        if not json_file.exists():
            return {"error": f"Không tìm thấy task {task_id}"}
        try:
            return json.loads(json_file.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def watch(self, client_id: str, task_id: str, poll: float = 5.0, timeout: float = 3600):
        """Block và theo dõi task cho đến khi xong."""
        print(f"[HOST] 👁 Đang theo dõi [{task_id}] trên {client_id}...")
        start = time.time()
        while True:
            info = self.get_task_status(client_id, task_id)
            status = info.get("status", "?")
            elapsed = int(time.time() - start)
            print(f"  [{elapsed:4d}s] {task_id}: {status}", end="\r")
            
            if status in ("DONE", "FAILED", "CANCELLED"):
                print()
                icon = "✓" if status == "DONE" else "✗"
                print(f"[HOST] {icon} Task [{task_id}] kết thúc: {status} | exit_code={info.get('exit_code')}")
                log_rel = info.get("log_file")
                if log_rel:
                    # log_file trong JSON là relative → resolve theo base_dir của Host
                    log_abs = self.base_dir / log_rel if not Path(log_rel).is_absolute() else Path(log_rel)
                    print(f"       Log: {log_abs}")
                return info
            
            if time.time() - start > timeout:
                print()
                print(f"[HOST] ⏰ Timeout sau {timeout}s")
                return info
            
            time.sleep(poll)

    # ─── LIST CLIENTS ─────────────────────────────────────────────────
    def list_clients(self) -> list[dict]:
        """Liệt kê tất cả client và trạng thái của chúng."""
        clients = []
        for d in sorted(self.base_dir.iterdir()):
            hb = d / "heartbeat.json"
            if d.is_dir() and d.name.startswith("client") and hb.exists():
                try:
                    info = json.loads(hb.read_text(encoding="utf-8"))
                    clients.append(info)
                except Exception:
                    clients.append({"client_id": d.name, "status": "UNKNOWN"})
        return clients

    def print_clients(self):
        clients = self.list_clients()
        if not clients:
            print("[HOST] Không tìm thấy client nào.")
            return
        print(f"\n{'ID':<12} {'STATUS':<8} {'TASK':<30} {'HEARTBEAT'}")
        print("-" * 75)
        for c in clients:
            print(f"{c.get('client_id','?'):<12} {c.get('status','?'):<8} "
                  f"{str(c.get('current_task','idle')):<30} {c.get('timestamp','')}")

    def list_pending_tasks(self, client_id: str) -> list[dict]:
        """Liệt kê các task đang PENDING hoặc RUNNING."""
        result = []
        req_dir = self._req_dir(client_id)
        for f in sorted(req_dir.glob("*.json")):
            try:
                action = json.loads(f.read_text(encoding="utf-8"))
                if action.get("status") in ("PENDING", "RUNNING"):
                    result.append(action)
            except Exception:
                pass
        return result


# ─────────────────────────────────────────
# CLI đơn giản để test
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys

    host = HostOrchestrator()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python host_orchestrator.py clients")
        print("  python host_orchestrator.py train <client_id> <config_json>")
        print("  python host_orchestrator.py kill  <client_id>")
        print("  python host_orchestrator.py status <client_id>")
        print("  python host_orchestrator.py watch  <client_id> <task_id>")
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "clients":
        host.print_clients()

    elif cmd == "train" and len(sys.argv) >= 4:
        client_id   = sys.argv[2]
        config_path = sys.argv[3]
        task_id = host.send_train(client_id, config_path)
        print(f"[HOST] Training task gửi xong: {task_id}")

    elif cmd == "kill" and len(sys.argv) >= 3:
        client_id = sys.argv[2]
        task_id = host.send_kill(client_id)

    elif cmd == "status" and len(sys.argv) >= 3:
        client_id = sys.argv[2]
        task_id = host.send_status_check(client_id)
        print(f"[HOST] Đã gửi yêu cầu status: {task_id}")

    elif cmd == "watch" and len(sys.argv) >= 4:
        client_id = sys.argv[2]
        task_id   = sys.argv[3]
        host.watch(client_id, task_id)

    else:
        print("Lệnh không hợp lệ. Chạy không có args để xem hướng dẫn.")
