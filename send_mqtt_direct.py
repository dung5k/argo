import paho.mqtt.client as mqtt
import json
import ssl

broker = 'broker.emqx.io'
port = 8883
topic = 'argo/network/v1/agents/Argo2/inbox'

def on_connect(client, userdata, flags, rc):
    payload = json.dumps({
        "from": "Argo1",
        "command": "Sếp Lê nhắc: Bên bạn (Argo2) đang load nhầm token tele của e-bot đấy, hãy kiểm tra lại cấu hình."
    })
    client.publish(topic, payload)
    client.disconnect()

client = mqtt.Client()
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.on_connect = on_connect
client.connect(broker, port, 60)
client.loop_forever()
