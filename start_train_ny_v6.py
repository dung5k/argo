import subprocess
import os
import sys
import time

run_id = "run_20260525_224500_v6_ny_mtf_expansion_cpu"
config_path = r"workspaces\CFG_XAG_NY_V6\runs\run_20260525_224500_v6_ny_mtf_expansion_cpu\config.json"

env = dict(os.environ,
    PYTHONIOENCODING="utf-8",
    PYTHONUTF8="1",
    PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:32",
    FORCE_CPU="1"
)

print("Generating new dataset tensors for NY V6...")
with open("upload_v6_ny.log", "w", encoding="utf-8") as f_log:
    sp1 = subprocess.run(
        [r"C:\argo\venv\Scripts\python.exe", "scripts/prepare_v6_dataset.py", "--config", config_path, "--no-upload"],
        env=env,
        stdout=f_log,
        stderr=subprocess.STDOUT
    )

if sp1.returncode != 0:
    print("Error generating dataset, check upload_v6_ny.log")
    sys.exit(1)

print("Dataset generation completed. Starting NY V6 training on CPU...")
log_file = open("train_v6_ny.log", "w", encoding="utf-8")

proc = subprocess.Popen(
    [r"C:\argo\venv\Scripts\python.exe", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"],
    stdout=log_file,
    stderr=subprocess.STDOUT,
    env=env
)
print("Training started on CPU. PID:", proc.pid)
with open("ny_v6_cpu_pid.txt", "w") as f_pid:
    f_pid.write(str(proc.pid))

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
    subprocess.run([r"C:\argo\venv\Scripts\python.exe", ".agent/notify_done.py", "xag_v6_training_done"], env=env)
