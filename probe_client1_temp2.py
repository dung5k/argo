import paho.mqtt.client as mqtt
import time
import json

msgs = []
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        msg_str = data.get('message', str(data))
    except:
        msg_str = msg.payload.decode('utf-8', errors='replace')
    msgs.append(f"[{msg.topic}] {msg_str}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"probe2_client1_123")
client.on_message = on_message
client.connect('broker.emqx.io', 1883, 60)
client.subscribe('argo_dungla_9213/client1/log')
client.subscribe('argo_dungla_9213/client1/agent_status')
client.loop_start()

print("Dang nghe trom client1 log trong 10 giay...")
time.sleep(10)
client.loop_stop()
client.disconnect()

for log in msgs[-10:]: print(log.strip())
