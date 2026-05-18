import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
root_tensors = "workspaces/CFG_LTC_LONDON_V6/data/tensors"
if os.path.exists(root_tensors):
    for fn in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, fn))

print("[PHASE 1] BUILD TENSORS...", flush=True)
r = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"workspaces\CFG_LTC_LONDON_V6\runs\run_20260515_171732_v6_LONDON_15m_BTC_Drop15_111\config.json", "--no-upload"], env=env)
if r.returncode != 0:
    print("FATAL: prepare failed"); sys.exit(1)

run_tensors = r"workspaces\CFG_LTC_LONDON_V6\runs\run_20260515_171732_v6_LONDON_15m_BTC_Drop15_111/data/tensors"
os.makedirs(run_tensors, exist_ok=True)
for fn in os.listdir(root_tensors):
    if fn.endswith(".npy") or fn.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, fn), os.path.join(run_tensors, fn))

print("[PHASE 2] START TRAINING...", flush=True)
proc = subprocess.Popen(
    [sys.executable, "-u", "src/training_v6/train_v6.py", r"workspaces\CFG_LTC_LONDON_V6\runs\run_20260515_171732_v6_LONDON_15m_BTC_Drop15_111\config.json", "--run-id", "run_20260515_171732_v6_LONDON_15m_BTC_Drop15_111", "--scratch"],
    stdout=open("train_v6_london.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT, env=env
)
print("PID:", proc.pid)
