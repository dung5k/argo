import sys, os, time
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)

import threading
threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()

print("Dang gui fix numpy cho client1...")
ctrl.send_command(cmd="run", raw=True, script="fix_numpy.py")

time.sleep(2)
ctrl.client_id = "clientGH"
ctrl.cmd_topic = "argo_dungla_9213/clientGH/cmd"
print("Dang gui fix numpy cho clientGH...")
ctrl.send_command(cmd="run", raw=True, script="fix_numpy.py")

time.sleep(5)
print("Xong!")
