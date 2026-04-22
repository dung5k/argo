import sys
import paho.mqtt.client as mqtt
import time

msg_count = 0

def on_message(client, userdata, message):
    global msg_count
    payload = message.payload.decode("utf-8")
    topic = message.topic
    print(f"[{topic}] {payload}")
    msg_count += 1
    if "OOM" in payload or "CUDA out of memory" in payload:
        print("\n\n>>> PHÁT HIỆN LỖI OOM !!!! <<<\n")
        sys.exit(1)
        
client = mqtt.Client(client_id="TestHostMonitor")
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("argo_dungla_9213/#", qos=1)

print("Đang lắng nghe log 20s xem có OOM không...")
client.loop_start()
time.sleep(20)
client.loop_stop()

if msg_count > 0:
    print(f"Bình thường. Đã nhận {msg_count} tin nhắn.")
    sys.exit(0)
else:
    print("Không có log nào.")
    sys.exit(0)
