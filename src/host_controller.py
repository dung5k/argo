import time
import json
import argparse
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
PREFIX = "argo_dungla_9213"

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

    def send_command(self, cmd: str, symbol: str = "xauusd"):
        if not self.connected:
            print("[HOST] Đang đợi kết nối...")
            for _ in range(50):
                if self.connected: break
                time.sleep(0.1)
        
        payload = json.dumps({"cmd": cmd, "symbol": symbol})
        self.client.publish(self.cmd_topic, payload, qos=1)
        print(f"[HOST] Lệnh '{cmd}' ({symbol}) đã được phát sóng lên kênh: {self.cmd_topic}")

    def listen_logs(self, timeout: int = 15):
        print(f"[HOST] Đang lắng nghe log trực tiếp từ {self.client_id} (thời gian: {timeout}s)...")
        print("-" * 60)
        time.sleep(timeout)
        print("-" * 60)
        print("[HOST] Đã kết thúc phiên nghe lén.")

def main():
    parser = argparse.ArgumentParser("Host Controller - ARGO AI")
    parser.add_argument("cmd", choices=["train", "kill", "listen"])
    parser.add_argument("--client-id", "-c", required=True)
    parser.add_argument("--symbol", "-s", default="xauusd")
    parser.add_argument("--time", "-t", type=int, default=15, help="Thời gian nghe log (giây)")
    
    args = parser.parse_args()
    
    host = HostController(args.client_id)
    host.client.connect(BROKER, PORT, 60)
    host.client.loop_start()
    
    if args.cmd in ["train", "kill"]:
        host.send_command(args.cmd, args.symbol)
        # Lắng nghe 1 lúc để xem phản hồi
        host.listen_logs(args.time)
    elif args.cmd == "listen":
        host.listen_logs(args.time)
        
    host.client.loop_stop()
    host.client.disconnect()

if __name__ == "__main__":
    main()
