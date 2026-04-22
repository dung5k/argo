import paho.mqtt.client as mqtt

def on_message(client, userdata, message):
    payload = message.payload.decode("utf-8")
    topic = message.topic
    print(f"[{topic}] {payload}")

client = mqtt.Client(client_id="TestHostMonitorInf")
client.on_message = on_message
client.connect("broker.emqx.io", 1883, 60)
client.subscribe("argo_dungla_9213/#", qos=1)

print("Đang lắng nghe log TẤT CẢ các client...")
client.loop_forever()
