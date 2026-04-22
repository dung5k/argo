import os
import glob

log_dir = r"C:\argo\logs\client1"
logs = sorted(glob.glob(os.path.join(log_dir, "tg_agent_*.log")))
if logs:
    with open(logs[-1], "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        print(''.join(lines[-100:]))
else:
    print("No log files found.")
