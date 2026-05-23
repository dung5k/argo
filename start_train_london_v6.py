import subprocess
import os
import sys

run_id = "run_20260523_212500_v6_london_init"
config_path = r"workspaces\CFG_XAG_LONDON_V6\runs\run_20260523_212500_v6_london_init\config.json"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", FORCE_CPU="0")

print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen(
    [r"C:\argo\venv\Scripts\python.exe", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"],
    stdout=open("train_v6_london.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    env=env,
    creationflags=0x00000008,
    close_fds=True
)
print("Training started in background. PID:", proc.pid)
