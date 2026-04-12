import paho.mqtt.client as mqtt
import time, json, sys, os
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

def on_message(c, u, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        if data.get("level") in ["RUN_OUT", "RUN_ERR", "ERR"]:
            print(f"GOT MSG: {data.get('level')}")
            with open("remote_client1.log", "a", encoding="utf-8") as f:
                f.write(data.get('message') + "\n==========\n")
            # don't disconnect immediately to catch trailing outputs
    except Exception as e:
        print(f"Loi decode: {e}")

client = mqtt.Client(client_id="TestLoggerFetch11")
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("argo_dungla_9213/client1/log", qos=1)
client.loop_start()

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)
ctrl.send_command('run', raw=True, script='print_log_v2.py')

print("Waiting for response...")
time.sleep(10)
client.loop_stop()
