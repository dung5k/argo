import time
import json
import os
import argparse
import base64
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
PREFIX = "argo_dungla_9213"
MAX_DIRECT_SIZE = 512 * 1024  # 512KB - gửi thẳng qua MQTT

class HostController:
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.cmd_topic = f"{PREFIX}/{client_id}/cmd"
        self.log_topic = f"{PREFIX}/{client_id}/log"
        
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[HOST] Đã kết nối với máy chủ vô tuyến ({BROKER})")
            self.connected = True
            self.client.subscribe(self.log_topic)
        else:
            print(f"[HOST] Lỗi kết nối: code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            level = data.get("level", "INFO")
            text = data.get("message", "")
            print(f"[{level}] {text}")
        except Exception:
            print(f"[RAW LOG] {msg.payload.decode('utf-8', errors='replace')}")

    def _wait_connected(self):
        if not self.connected:
            print("[HOST] Đang đợi kết nối...")
            for _ in range(50):
                if self.connected: break
                time.sleep(0.1)

    def send_command(self, cmd: str, symbol: str = "xauusd", script: str = "", raw: bool = False):
        self._wait_connected()
        
        if cmd == "run" and raw and script:
            try:
                with open(script, "r", encoding="utf-8") as f:
                    code_content = f.read()
                payload = json.dumps({"cmd": "run_code", "code": code_content})
                print(f"[HOST] Đang nén RAW CODE ({len(code_content)} ký tự) để gửi trực tiếp...")
            except Exception as e:
                print(f"[LỖI] Đọc file raw_code thất bại: {e}")
                return
        else:
            payload = json.dumps({"cmd": cmd, "symbol": symbol, "script": script})
            
        self.client.publish(self.cmd_topic, payload, qos=1)
        print(f"[HOST] Lệnh '{cmd}{' (RAW)' if raw else ''}' đã được phát sóng lên kênh: {self.cmd_topic}")

    def send_file(self, local_path: str, remote_dest: str):
        """
        Gửi file từ Host sang Client.
        - File <= 512KB: gửi thẳng qua MQTT (base64)
        - File > 512KB : upload lên HuggingFace rồi báo Client kéo về
        """
        self._wait_connected()

        if not os.path.exists(local_path):
            print(f"[LỖI] Không tìm thấy file: {local_path}")
            return

        file_size = os.path.getsize(local_path)
        file_name = os.path.basename(local_path)

        if file_size <= MAX_DIRECT_SIZE:
            # === GỬI THẲNG QUA MQTT (Base64) ===
            with open(local_path, "rb") as f:
                raw_bytes = f.read()
            b64_content = base64.b64encode(raw_bytes).decode("utf-8")
            payload = json.dumps({
                "cmd": "receive_file",
                "dest": remote_dest,
                "filename": file_name,
                "content_b64": b64_content,
                "size": file_size
            })
            self.client.publish(self.cmd_topic, payload, qos=1)
            print(f"[HOST] 📁 Gửi file '{file_name}' ({file_size/1024:.1f}KB) thẳng qua MQTT → {remote_dest}")
        else:
            # === FILE LỚN: Upload lên HuggingFace rồi báo Client kéo về ===
            print(f"[HOST] 📦 File '{file_name}' lớn ({file_size/1024/1024:.1f}MB) — Upload HuggingFace trước...")
            try:
                import sys
                hf_sync_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
                sys.path.insert(0, hf_sync_path)
                from hf_sync import _load_config
                from huggingface_hub import HfApi
                
                cfg = _load_config()
                if not cfg:
                    print("[LỖI] Không đọc được tg_config.json")
                    return
                
                api = HfApi()
                api.upload_file(
                    path_or_fileobj=local_path,
                    path_in_repo=remote_dest,
                    repo_id=cfg["hf_repo_id"],
                    repo_type="dataset",
                    token=cfg["hf_token"],
                    commit_message=f"Send file: {file_name}"
                )
                print(f"[HOST] ☁️ Đã upload '{file_name}' lên HuggingFace tại '{remote_dest}'")

                # Báo Client kéo file về từ HF
                payload = json.dumps({
                    "cmd": "pull_hf_file",
                    "hf_path": remote_dest,
                    "local_dest": remote_dest
                })
                self.client.publish(self.cmd_topic, payload, qos=1)
                print(f"[HOST] 📡 Đã báo Client kéo file từ HF về: {remote_dest}")
            except Exception as e:
                print(f"[LỖI] Upload HF thất bại: {e}")

    def deploy_agent(self, version: str = "latest"):
        """
        Deploy một version cụ thể của agent sang Client.
        - version='latest' → dùng file hiện tại
        - version='v1.3.5' → dùng file trong versions/client_tg_agent_v1.3.5.py
        """
        self._wait_connected()

        base_dir = os.path.dirname(os.path.abspath(__file__))
        versions_dir = os.path.join(base_dir, "versions")
        agent_src = os.path.join(base_dir, "client_tg_agent.py")

        if version == "latest":
            target_file = agent_src
            ver_label = "latest"
        else:
            target_file = os.path.join(versions_dir, f"client_tg_agent_{version}.py")
            ver_label = version

        if not os.path.exists(target_file):
            print(f"[LỖI] Không tìm thấy file: {target_file}")
            print(f"[INFO] Các version hiện có:")
            if os.path.exists(versions_dir):
                for f in sorted(os.listdir(versions_dir)):
                    print(f"  - {f}")
            return

        with open(target_file, "rb") as f:
            raw_bytes = f.read()
        import base64
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        file_size = len(raw_bytes)

        payload = json.dumps({
            "cmd": "deploy_agent",
            "version": ver_label,
            "content_b64": b64,
            "size": file_size
        })
        self.client.publish(self.cmd_topic, payload, qos=1)
        print(f"[HOST] 🚀 Deploy agent {ver_label} ({file_size/1024:.1f}KB) → {self.client_id} (client sẽ tự restart)")

    @staticmethod
    def save_version(tag: str = ""):
        """Lưu phiên bản hiện tại của agent vào thư mục versions/ với tag version."""
        import shutil, datetime
        base_dir = os.path.dirname(os.path.abspath(__file__))
        versions_dir = os.path.join(base_dir, "versions")
        os.makedirs(versions_dir, exist_ok=True)
        agent_src = os.path.join(base_dir, "client_tg_agent.py")

        if not tag:
            tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(versions_dir, f"client_tg_agent_{tag}.py")
        shutil.copy2(agent_src, dest)
        print(f"[HOST] 💾 Đã lưu version: {dest}")
        # Liệt kê tất cả versions
        print("[HOST] Danh sách versions hiện có:")
        for f in sorted(os.listdir(versions_dir)):
            fpath = os.path.join(versions_dir, f)
            sz = os.path.getsize(fpath) / 1024
            print(f"  - {f} ({sz:.1f}KB)")
        return dest


    def sync_data_to_client(self):

        self._wait_connected()
        print("[HOST] 📤 Đang đẩy data/ lên HuggingFace...")
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from hf_sync import push_data
            push_data()
        except Exception as e:
            print(f"[LỖI] push_data thất bại: {e}")
            return

        payload = json.dumps({"cmd": "pull_hf_data"})
        self.client.publish(self.cmd_topic, payload, qos=1)
        print(f"[HOST] 📡 Đã báo Client ({self.client_id}) kéo data mới từ HuggingFace.")

    def listen_logs(self, timeout: int = 15):
        print(f"[HOST] Đang lắng nghe log trực tiếp từ {self.client_id} (thời gian: {timeout}s)...")
        print("-" * 60)
        time.sleep(timeout)
        print("-" * 60)
        print("[HOST] Đã kết thúc phiên nghe lén.")


def main():
    parser = argparse.ArgumentParser("Host Controller - ARGO AI")
    parser.add_argument("cmd", choices=["train", "kill", "listen", "run", "update", "send_file", "sync_data", "deploy_agent", "save_version"])
    parser.add_argument("--client-id", "-c", default="")
    parser.add_argument("--symbol", "-s", default="xauusd")
    parser.add_argument("--script", default="")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--file", default="")
    parser.add_argument("--dest", default="")
    parser.add_argument("--version", "-v", default="latest", help="Version agent cần deploy (VD: v1.3.5 hoặc latest)")
    parser.add_argument("--tag", default="", help="Tag version khi lưu (VD: v1.3.5). Mặc định: timestamp")
    parser.add_argument("--time", "-t", type=int, default=15)
    
    args = parser.parse_args()

    # Các lệnh không cần kết nối MQTT
    if args.cmd == "save_version":
        HostController.save_version(args.tag)
        return

    if not args.client_id:
        print("[LỖI] Cần truyền --client-id (-c)")
        return

    host = HostController(args.client_id)
    host.client.connect(BROKER, PORT, 60)
    host.client.loop_start()

    if args.cmd == "send_file":
        if not args.file or not args.dest:
            print("[LỖI] Cần truyền --file và --dest.")
        else:
            host.send_file(args.file, args.dest)
            host.listen_logs(args.time)
    elif args.cmd == "sync_data":
        host.sync_data_to_client()
        host.listen_logs(args.time)
    elif args.cmd == "deploy_agent":
        host.deploy_agent(args.version)
        host.listen_logs(args.time)
    elif args.cmd in ["train", "kill", "run", "update"]:
        host.send_command(args.cmd, args.symbol, args.script, getattr(args, 'raw', False))
        host.listen_logs(args.time)
    elif args.cmd == "listen":
        host.listen_logs(args.time)

    host.client.loop_stop()
    host.client.disconnect()


if __name__ == "__main__":
    main()
