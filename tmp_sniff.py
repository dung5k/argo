import paho.mqtt.client as mqtt
import time
import json
import sys

lines = []
def on_message(client, userdata, msg):
    payload = msg.payload.decode('utf-8')
    try:
        data = json.loads(payload)
        lines.append(f"[{data.get('level', '')}] {data.get('message', '')}")
    except:
        lines.append(payload)

client = mqtt.Client()
client.on_message = on_message
client.connect('broker.emqx.io', 1883, 60)
client.subscribe('argo_dungla_9213/clientGH/log')
client.loop_start()

print("Listening for 90s...")
time.sleep(90)
client.loop_stop()
client.disconnect()

for line in lines:
    print(line)
