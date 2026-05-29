import subprocess
import os
import sys

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
proc1 = subprocess.Popen(
    [sys.executable, "-u", "src/bot_v6/bot_v6.py", "bot_config_v6_ltc.json", "bot_schedule_v6_ltc.json"],
    stdout=open("bot_ltc_live.log", "a", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    env=env,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print("Started Bot with PID:", proc1.pid)

proc2 = subprocess.Popen(
    [sys.executable, "-u", "autonomous_training_loop.py", "--symbol", "LTC"],
    stdout=open("training_ltc.log", "a", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    env=env,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print("Started Training Loop with PID:", proc2.pid)
