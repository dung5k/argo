import subprocess
import os
import sys
import time

run_id = "run_20260523_212500_v6_london_init"
config_path = r"workspaces\CFG_XAG_LONDON_V6\runs\run_20260523_212500_v6_london_init\config.json"
env = dict(os.environ,
    PYTHONIOENCODING="utf-8",
    PYTHONUTF8="1",
    # GPU Training: fix CUDA memory fragmentation on GTX 1660 SUPER (6GB VRAM)
    PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:128",
    FORCE_CPU="0"
)

print("Starting London V6 Training on GPU (scratch)...")
log_file = open("train_v6_london.log", "w", encoding="utf-8")

proc = subprocess.Popen(
    [r"C:\argo\venv\Scripts\python.exe", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    env=env
)
print("Training started on GPU. PID:", proc.pid)

try:
    while proc.poll() is None:
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping training...")
    proc.terminate()
finally:
    log_file.close()
    print("Training finished with code:", proc.returncode)
    
    # Notify completion to trigger the next State Machine run
    print("Sending trigger: xag_v6_training_done...")
    subprocess.run([sys.executable, ".agent/notify_done.py", "xag_v6_training_done"], env=env)

