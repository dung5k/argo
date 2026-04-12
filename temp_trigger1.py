import sys
import time
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.orchestration.host_controller import HostController, BROKER, PORT

if __name__ == "__main__":
    print("[1] Kết nối MQTT tới client1...")
    ctrl = HostController(client_id="client1")
    ctrl.client.connect(BROKER, PORT, 60)
    threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()
    
    print("[2] Gửi lệnh STOP TRAIN tới client1...")
    import json
    ctrl.client.publish("argo_dungla_9213/client1/cmd", json.dumps({"cmd": "stop_train"}), qos=1)
    time.sleep(3) # Cho thoi gian dung tien trinh
    
    print("[3] Gửi lệnh DEPLOY tới client1...")
    ctrl.deploy_agent("latest")
    
    print("[4] Chờ 25 giây để client1 tiến hành Hard Reset, Git Pull và khởi động lại...")
    time.sleep(25)
    
    print("[5] Gửi lệnh TRAIN tới client1 cho XAU_ASIAN_V2...")
    ctrl.send_command(cmd="train", symbol="xau_asian_v2", session="asian")
    
    time.sleep(3)
    print("Xong!")
    sys.exit(0)
