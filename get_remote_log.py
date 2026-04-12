import sys, os, time
sys.path.insert(0, os.getcwd())
from src.orchestration.host_controller import HostController

ctrl = HostController(client_id='client1')
ctrl.client.connect('broker.emqx.io', 1883, 60)

import threading
threading.Thread(target=ctrl.client.loop_forever, daemon=True).start()

print("Dang gui ma hien thi log cho client1...")

# Tạo mã Python để chạy MẶT TRẬN CLIENT
raw_code = """
import os

log_path = r"C:\\argo\\logs\\client1_unified.log"
try:
    if not os.path.exists(log_path):
        print(f"Log path khong ton tai: {log_path}")
    else:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        print("===== LAST 40 LINES OF CLIENT1 LOG =====")
        print("".join(lines[-40:]))
except Exception as e:
    print(f"Loi doc log: {e}")
"""

# Ghi mã vô file cục bộ để truyền đi
with open("temp_log_reader.py", "w", encoding="utf-8") as f:
    f.write(raw_code)

ctrl.send_command(cmd="run", raw=True, script="temp_log_reader.py")

time.sleep(5)
print("Xong!")
