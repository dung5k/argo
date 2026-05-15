import subprocess
import os
import sys

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

# Khởi chạy XAG Bot (Virtual Env)
p1 = subprocess.Popen([
    r"C:\argo\venv\Scripts\python.exe", "-u", "src/bot_v3/bot_v3.py", 
    "bot_config_xag.json", "bot_schedule_xag.json"
], stdout=open("xag_bot.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)

# Khởi chạy LTC Bot (Virtual Env)
p2 = subprocess.Popen([
    r"C:\argo\venv\Scripts\python.exe", "-u", "src/bot_v6/bot_v6.py", 
    "bot_config_v6_ltc.json", "bot_schedule_v6_ltc.json"
], stdout=open("ltc_bot.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)

print(f"XAG Bot PID: {p1.pid}")
print(f"LTC Bot PID: {p2.pid}")
