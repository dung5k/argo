import glob
import subprocess

runs = glob.glob("runs/*/*.log")
runs.sort(key=os.path.getmtime)
out = "=== REMOTE LOG VIA CMD ===\n"
if runs:
    last_run = runs[-1]
    res = subprocess.run(["cmd", "/c", "type", last_run], capture_output=True, text=True, errors="replace")
    lines = res.stdout.splitlines()
    out += "\n".join(lines[-25:])
else:
    out += "NO RUN LOGS"

try:
    import paho.mqtt.client as mqtt
    import random
    import time
    cid = f"cmd_probe_{random.randint(100,999)}"
    client = mqtt.Client(client_id=cid)
    client.connect("broker.emqx.io", 1883, 60)
    client.loop_start()
    
    topic = "argo_dungla_9213/clientV2/log"
    payload = f"[{cid}] \n{out}"
    client.publish(topic, payload, qos=0)
    time.sleep(2)
    client.loop_stop()
    client.disconnect()
except Exception as e:
    pass
