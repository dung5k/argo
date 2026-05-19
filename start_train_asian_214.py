import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"
if os.path.exists(root_tensors):
    for f in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, f))
    print("Cleaned root tensors directory.")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_192408_v6_ASIAN_5m_BalancedCapacity_214\config.json", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] INJECT TENSORS INTO RUN DIRECTORY...", flush=True)
run_dir_tensors = r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_192408_v6_ASIAN_5m_BalancedCapacity_214/data/tensors"
os.makedirs(run_dir_tensors, exist_ok=True)
for f in os.listdir(root_tensors):
    if f.endswith(".npy") or f.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, f), os.path.join(run_dir_tensors, f))

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_192408_v6_ASIAN_5m_BalancedCapacity_214\config.json", "--run-id", "run_20260519_192408_v6_ASIAN_5m_BalancedCapacity_214", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
