import os, subprocess, sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
env = os.environ.copy()
env['PYTHONIOENCODING'] = 'utf-8'
run_dir = r"workspaces/CFG_LTC_LONDON_V6/runs/run_20260517_211958_v6_LONDON_Cross5m_Win180_116"
config = f"{run_dir}/config.json"
log_out = open(f"{run_dir}/train_log.txt", "w", encoding="utf-8")
log_err = open(f"{run_dir}/train_err.txt", "w", encoding="utf-8")
proc = subprocess.Popen(
    [sys.executable, "src/training_v6/train_v6.py", config],
    stdout=log_out, stderr=log_err, env=env,
    cwd=r"d:\DungLA\client1"
)
print(f"PID: {proc.pid}")
