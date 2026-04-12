import sys, os, time, json
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print(f"[{msg.topic}] {msg.payload.decode('utf-8')}")

client = mqtt.Client(client_id="TestLogger")
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("argo_dungla_9213/client1/log", qos=1)

print("Dang lang nghe log cua client1 trong 15s...")
client.loop_start()

# Gui lenh tiep xem no con tra loi khong
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController
ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)
ctrl.send_command(cmd="run", raw=True, script="get_remote_log.py")

time.sleep(15)
client.loop_stop()
