import sys, os, time, json
import paho.mqtt.client as mqtt

sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)
import threading
threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()

print("Sending kill to client1 to ensure it is not busy...")
ctrl.client.publish("argo_dungla_9213/client1/cmd", '{"cmd": "kill"}', qos=1)
time.sleep(1)

print("Gui lenh train xau_asian_v2...")
ctrl.send_command(cmd='train', symbol='xau_asian_v2', session='asian')
time.sleep(2)
print("Done sending. Bay gio dung monitor_all.py de xem ket qua.")
