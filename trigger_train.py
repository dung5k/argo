import sys, os, time
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)
import threading
threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()
time.sleep(1)
ctrl.send_command(cmd='train', symbol='xau_asian_v2', session='asian')
time.sleep(2)
print("Done")
