import os
import glob
import time

time.sleep(3) # Wait for listener to boot up

try:
    with open("logs/clientV2_master.log", "r", encoding="utf-8", errors="replace") as f:
        print("MASTER LOG ENDING:\n", "".join(f.readlines()[-15:]))
except Exception as e:
    print("MASTER LOG ERR:", e)

try:
    runs = glob.glob("runs/*/*.log")
    runs.sort(key=os.path.getmtime)
    if runs:
        with open(runs[-1], "r", encoding="utf-8", errors="replace") as f:
            print(f"RUN LOG ({runs[-1]}):\n", "".join(f.readlines()[-20:]))
    else:
        print("NO RUN LOGS FOUND.")
except Exception as e:
    print("RUN LOG ERR:", e)
