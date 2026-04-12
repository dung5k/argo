
import os

log_path = r"C:\argo\logs\client1_unified.log"
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
