import paho.mqtt.client as mqtt
import time, json, sys, os
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

# Payload
raw_code = """
import os, json, glob

runs_dir = r"C:\\argo\\logs\\runs"
if not os.path.exists(runs_dir):
    print("NO RUNS DIR")
else:
    folders = glob.glob(os.path.join(runs_dir, "run_*"))
    for d in sorted(folders)[-4:]:
        metrics_file = os.path.join(d, "metrics_log.json")
        if os.path.exists(metrics_file):
            print(f"\\n--- {os.path.basename(d)} ---")
            try:
                with open(metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                best_ep = max(data, key=lambda x: x.get("score", 0))
                print(f"BEST EPOCH Data:")
                for k, v in best_ep.items():
                    print(f"  {k}: {v}")
            except Exception as e:
                print(f"Loi doc json: {e}")
"""

with open("temp/fetch_metrics.py", "w", encoding="utf-8") as f:
    f.write(raw_code.strip())

def on_message(c, u, msg):
    try:
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        if data.get("level") in ["RUN_OUT", "RUN_ERR", "ERR"]:
            print(f"GOT REMOTE METRICS:\n{data.get('message')}")
    except Exception as e:
        print(f"Loi decode: {e}")

client = mqtt.Client(client_id="TestLoggerFetch33")
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("argo_dungla_9213/client1/log", qos=1)
client.loop_start()

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)
ctrl.send_command('run', raw=True, script='temp/fetch_metrics.py')

print("Waiting for response...")
time.sleep(10)
client.loop_stop()
