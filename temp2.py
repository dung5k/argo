import os
try:
    with open("logs/clientV2_master.log", "r", encoding="utf-8", errors="replace") as f:
        print("MASTER LOG:\n", "".join(f.readlines()[-20:]))
except Exception as e:
    print(e)
import glob
try:
    runs = glob.glob("runs/*/*.log")
    runs.sort(key=os.path.getmtime)
    with open(runs[-1], "r", encoding="utf-8", errors="replace") as f:
        print(f"RUN LOG ({runs[-1]}):\n", "".join(f.readlines()[-20:]))
except Exception as e:
    print(e)
