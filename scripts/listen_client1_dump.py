import paho.mqtt.client as mqtt
import json
import time

f = open("client1_logs_dump.txt", "w", encoding="utf-8")

def on_connect(client, userdata, flags, rc, *args):
    print("Connected")
    client.subscribe("argo_dungla_9213/client1/log")

def on_message(client, userdata, msg, *args):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
        level = data.get("level", "INFO")
        text = data.get("message", "")
        f.write(f"[{level}] {text}\n")
        f.flush()
        print(f"Received {level} log")
    except Exception as e:
        print("Error decoding", e)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)

client.loop_start()

# Now trigger the command via another process
import subprocess
print("Triggering run_code...")
with open("tmp_list_client1_logs.py", "r", encoding="utf-8") as script_f:
    code = script_f.read()
payload = json.dumps({"cmd": "run_code", "code": code})
client.publish("argo_dungla_9213/client1/cmd", payload, qos=1)

print("Waiting 15 seconds for logs to arrive...")
time.sleep(15)
client.loop_stop()
f.close()
print("Done, check client1_logs_dump.txt")
