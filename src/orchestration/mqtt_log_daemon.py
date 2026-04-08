import os
import json
import time
import datetime
from pathlib import Path
import paho.mqtt.client as mqtt

# ============================================================
# Cấu hình
# ============================================================
BROKER = "broker.emqx.io"
PORT = 1883
BASE_TOPIC = "argo_dungla_9213"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "clients"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[DAEMON] Đã kết nối MQTT Broker thành công!")
        # Lắng nghe hệ thống log của TẤT CẢ các client
        topic = f"{BASE_TOPIC}/+/log"
        client.subscribe(topic, qos=1)
        print(f"[DAEMON] Đang theo dõi Realtime Topic: {topic} (QoS=1)")
    else:
        print(f"[DAEMON] Lỗi kết nối MQTT, mã lỗi: {rc}")

def on_message(client, userdata, msg):
    try:
        # Topic format: argo_dungla_9213/{client_id}/log
        parts = msg.topic.split('/')
        if len(parts) >= 3:
            client_id = parts[1]
            payload = json.loads(msg.payload.decode('utf-8'))
            level = payload.get("level", "INFO")
            message = payload.get("message", "")
            timestamp = payload.get("ts", datetime.datetime.now().isoformat())
            
            # Khởi tạo thư mục log nếu chưa có
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = LOG_DIR / f"{client_id}.log"
            
            MAX_LOG_SIZE = 300 * 1024  # 300 KB
            if log_file.exists() and log_file.stat().st_size > MAX_LOG_SIZE:
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"[{datetime.datetime.now().isoformat()}] [SYSTEM] Log file vượt quá 300KB. Đã tự động xoá (Clear log) để giảm tải.\n")
                    
            # Ghi log realtime vào file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [{level}] {message}\n")
                
    except Exception as e:
        print(f"[DAEMON] Lỗi xử lý tin nhắn: {e}")

def main():
    print("======================================================")
    print("   MQTT LOG DAEMON - BỘ LẮNG NGHE LOG THỜI GIAN THỰC")
    print("======================================================")
    print(f"Log Output Dir: {LOG_DIR}")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_forever()
        except KeyboardInterrupt:
            print("\n[DAEMON] Đã dừng bởi người dùng.")
            break
        except Exception as e:
            print(f"[DAEMON] Lỗi: {e}. Thử kết nối lại sau 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
