import subprocess
import os
import sys
import time

run_id = "run_20260526_025000_v5_london_hyper_momentum_precision_cpu"
config_path = r"workspaces\CFG_XAG_LONDON_V5\runs\run_20260526_025000_v5_london_hyper_momentum_precision_cpu\config.json"

env = dict(os.environ,
    PYTHONIOENCODING="utf-8",
    PYTHONUTF8="1",
    CUDA_VISIBLE_DEVICES="",
    FORCE_CPU="1"
)

print("Generating new dataset tensors for LONDON V5 MTF Monthly Split...")
with open("upload_v5_london_expansion.log", "w", encoding="utf-8") as f_log:
    sp1 = subprocess.run(
        [r"C:\argo\venv\Scripts\python.exe", "scripts/prepare_v3_dataset.py", "--config", config_path, "--fast-hit-bars", "7", "--no-upload", "--monthly-split"],
        env=env,
        stdout=f_log,
        stderr=subprocess.STDOUT
    )

if sp1.returncode != 0:
    print("Error generating dataset, check upload_v5_london_expansion.log")
    sys.exit(1)

print("Dataset generation completed. Starting LONDON V5 MTF Expansion training on CPU...")

proc = subprocess.Popen(
    [r"C:\argo\venv\Scripts\python.exe", "-u", "src/training_v3/train_v3.py", config_path, "--run-id", run_id, "--scratch", "--log-to-file"],
    env=env
)
print("Training started on CPU. PID:", proc.pid)

with open("london_v5_cpu_pid.txt", "w") as f_pid:
    f_pid.write(str(proc.pid))

try:
    while proc.poll() is None:
        time.sleep(5)
except KeyboardInterrupt:
    print("Stopping training...")
    proc.terminate()
finally:
    print("Training finished with code:", proc.returncode)
