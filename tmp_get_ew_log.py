import os, subprocess
import paho.mqtt.client as mqtt
import json, time
import paho.mqtt.publish as publish

BROKER = "broker.emqx.io"
CLIENT = "clientEW"
CMD_TOPIC = f"argo_dungla_9213/{CLIENT}/cmd"
LOG_TOPIC = f"argo_dungla_9213/{CLIENT}/log"

logs_collected = []

def on_connect(c, u, f, rc):
    c.subscribe(LOG_TOPIC)

def on_message(c, u, msg):
    payload = msg.payload.decode('utf-8')
    try:
        data = json.loads(payload)
        logs_collected.append(data.get('message', payload))
        print("Received a log message.")
    except: pass

c = mqtt.Client()
c.on_connect = on_connect
c.on_message = on_message
c.connect(BROKER, 1883)
c.loop_start()

code = """
import glob, os
log_dir = "clientEW/logs"
try:
    sys_logs = glob.glob(os.path.join(log_dir, "tg_agent*.log"))
    if sys_logs:
        latest = max(sys_logs, key=os.path.getctime)
        with open(latest, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print("=== TG AGENT LOG ===")
            print("".join(lines[-150:]))
except Exception as e:
    print(e)
"""

payload = json.dumps({"cmd": "run_code", "code": code})
publish.single(CMD_TOPIC, payload, hostname=BROKER)

time.sleep(12)
c.loop_stop()

with open('tmp_clientEW_git.txt', 'w', encoding='utf-8') as f:
    for lg in logs_collected:
        f.write(lg + "\n")
print("Done writing to tmp_clientEW_git.txt")
