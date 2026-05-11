import json
import threading
import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 8883
PREFIX = "argo_dungla_9213"

class MqttHelper:
    def __init__(self, client_id: str, on_command_callback):
        self.client_id = client_id
        self.cmd_topic = f"{PREFIX}/{self.client_id}/cmd"
        self.log_topic = f"{PREFIX}/{self.client_id}/log"
        self.on_command_callback = on_command_callback
        
        # Paho MQTT 2.x re-introduced Client ID parameter correctly, but older version takes it directly. We use default.
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self._thread = None
        self._running = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT] Đã kết nối với máy chủ vô tuyến ({BROKER})")
            self.client.subscribe(self.cmd_topic)
        else:
            print(f"[MQTT] Lỗi kết nối: code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8")
            data = json.loads(payload)
            if self.on_command_callback:
                self.on_command_callback(data)
        except Exception as e:
            print(f"[MQTT] Loi doc lenh: {e}")

    def start(self):
        self._running = True
        
        # Thiết lập Di chúc điện tử (LWT) trước khi kết nối
        lwt_payload = json.dumps({
            "level": "STATUS",
            "message": "💀 OFFLINE (Bị sập đột ngột)"
        })
        self.client.will_set(self.log_topic, payload=lwt_payload, qos=1, retain=True)
        
        if PORT == 8883:
            self.client.tls_set() # Kích hoạt SSL/TLS
            
        self.client.connect(BROKER, PORT, 60)
        self._thread = threading.Thread(target=self.client.loop_forever, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()

    def send_log(self, level: str, message: str, retain: bool = False):
        if not self._running:
            return
        payload = json.dumps({
            "level": level,
            "message": message
        })
        self.client.publish(self.log_topic, payload, qos=1, retain=retain)
