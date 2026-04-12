import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.orchestration.host_controller import HostController, BROKER, PORT

ctrl1 = HostController(client_id="client1")
ctrl1.client.connect(BROKER, PORT, 60)
ctrlGH = HostController(client_id="clientGH")
ctrlGH.client.connect(BROKER, PORT, 60)

ctrl1.send_command(cmd="train", symbol="xau_asian_v2", session="asian")
time.sleep(2)
ctrlGH.send_command(cmd="train", symbol="arb_v2", session="weekend")
time.sleep(2)
print("Xong!")
