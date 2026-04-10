"""
Gửi lệnh training v1.5.1 tới clientGH qua MQTT với PYTHONPATH đúng.
"""
import json
import time
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT   = 1883
TOPIC  = "argo_dungla_9213/clientGH/cmd"

# Bootstrap script chạy trên client - set PYTHONPATH = project root
bootstrap = (
    "import subprocess, sys, os\n"
    "proj = os.getcwd()\n"
    "env = dict(os.environ)\n"
    "env['PYTHONPATH'] = proj\n"
    "proc = subprocess.Popen(\n"
    "    [sys.executable, 'src/training_v1_5/train_v1_5.py', 'data/bot_config_xau_v1_5.json'],\n"
    "    cwd=proj, env=env\n"
    ")\n"
    "print(f'[TRAIN V1.5.1] Started PID={proc.pid} | XAUUSD | config=bot_config_xau_v1_5.json')\n"
)

payload = json.dumps({"cmd": "run_code", "code": bootstrap})

connected = False

def on_connect(client, userdata, flags, rc, *args):
    global connected
    if hasattr(rc, "value"):
        rc = rc.value
    if rc == 0:
        connected = True
        print("[HOST] Đã kết nối MQTT broker")

def on_publish(client, userdata, mid, *args):
    print(f"[HOST] Lệnh training v1.5.1 đã gửi thành công (mid={mid})")

client = mqtt.Client()
client.on_connect = on_connect
client.on_publish  = on_publish
client.connect(BROKER, PORT, 60)
client.loop_start()

for _ in range(50):
    if connected:
        break
    time.sleep(0.1)

if not connected:
    print("[LỖI] Không kết nối được MQTT!")
else:
    client.publish(TOPIC, payload, qos=1)
    time.sleep(4)
    print("[HOST] Done. clientGH đang khởi động train_v1_5.py...")

client.loop_stop()
client.disconnect()
