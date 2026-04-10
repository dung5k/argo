import paho.mqtt.client as mqtt
import json, time

# Clear old file
open("client_status_dump.txt", "w", encoding="utf-8").close()

def on_msg(c, u, msg):
    try:
        p = json.loads(msg.payload)
        if p.get("level") == "RUN_OUT":
            with open("client_status_dump.txt", "a", encoding="utf-8") as f:
                f.write(f"[{msg.topic}]\n{p.get('message')}\n---\n")
    except: pass

c = mqtt.Client()
c.on_message = on_msg
c.connect("broker.emqx.io", 1883, 60)
c.subscribe("argo_dungla_9213/+/log")
c.loop_start()

time.sleep(1)

code = """
import glob
import os
import sys

# Try multiple locations to find log file
files = glob.glob('*/logs/*_unified.log') + glob.glob('logs/*_unified.log')
res = []
for f in files:
    try:
        lines = open(f, 'r', encoding='utf-8', errors='replace').readlines()
        head = [x.strip() for x in lines[:25] if 'CMD' in x or 'bot_config' in x or 'script' in x or 'TRANSFORMER V' in x]
        res.append('FILE: ' + f)
        res.extend(head)
    except Exception as e: res.append(str(e))

if not res:
    res.append("No config found. CWD=" + os.getcwd())

print('\\n'.join(res))
"""

print("Sending MQTT run_code...")
for cl in ["clientEW"]:
    c.publish(f"argo_dungla_9213/{cl}/cmd", json.dumps({"cmd": "run_code", "code": code}))

time.sleep(10)
c.loop_stop()
print("Done")
