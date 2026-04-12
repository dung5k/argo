import os
log_path = r"C:\argo\logs\client1_unified.log"
try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        print("".join(f.readlines()[-200:]))
except Exception as e:
    print("LOI: ", str(e))
