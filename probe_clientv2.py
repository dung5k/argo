import os
import glob
import json
import time

out = "=== TRACING CLIENTV2 ===\n"

try:
    runs = glob.glob("runs/*/*.log")
    runs.sort(key=os.path.getmtime)
    if runs:
        last_run = runs[-1]
        with open(last_run, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            out += f"RUN LOG ({last_run}):\n"
            out += "".join(lines[-25:])
    else:
        out += "NO RUN LOGS FOUND.\n"
except Exception as e:
    out += f"Error scanning runs: {e}"

try:
    import paho.mqtt.client as mqtt
    import random
    cid = f"temp_probe_{random.randint(100,999)}"
    client = mqtt.Client(client_id=cid)
    client.connect("broker.emqx.io", 1883, 60)
    client.loop_start()
    
    topic = "argo_dungla_9213/clientV2/log"
    import sys
    payload = f"[{cid}] \n{out}"
    client.publish(topic, payload, qos=0)
    
    time.sleep(2)
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print("MQTT ERR:", e)

print("Probe Finished.")
