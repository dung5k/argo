import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.orchestration.host_controller import HostController, BROKER, PORT

if __name__ == "__main__":
    print("[1] Kết nối MQTT tới client1...")
    ctrl = HostController(client_id="client1")
    ctrl.client.connect(BROKER, PORT, 60)
    import threading
    threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()
    
    time.sleep(2) # Cho phep connect
    print("[2] Gửi lệnh TRAIN tới client1 cho XAU_ASIAN_V2...")
    ctrl.send_command(cmd="train", symbol="xau_asian_v2", session="asian")
    
    time.sleep(3)
    print("Xong!")
    sys.exit(0)
