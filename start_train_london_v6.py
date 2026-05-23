import subprocess
import os
import sys
import time

run_id = "run_20260523_212500_v6_london_init"
config_path = r"workspaces\CFG_XAG_LONDON_V6\runs\run_20260523_212500_v6_london_init\config.json"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", FORCE_CPU="1")

print("Starting London V6 Training in persistent background...")
log_file = open("train_v6_london.log", "w", encoding="utf-8")

proc = subprocess.Popen(
    [r"C:\argo\venv\Scripts\python.exe", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    env=env
)
print("Training started. PID:", proc.pid)

try:
    while proc.poll() is None:
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping training...")
    proc.terminate()
finally:
    log_file.close()
    print("Training finished with code:", proc.returncode)
