# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import shutil

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
if os.path.exists(root_tensors):
    for f in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, f))
    print("Cleaned root tensors directory.")

print(">>> [PHASE 0.1] PREPARE RAW DATA PARQUETS...", flush=True)
raw_dir = "workspaces/CFG_LTC_ASIAN_V6/data/raw"
os.makedirs(raw_dir, exist_ok=True)
for sym_file in ["LTCUSDT_2024_2026_M1.parquet", "BTCUSDT_2024_2026_M1.parquet", "ETHUSDT_2024_2026_M1.parquet"]:
    src = os.path.join("data/history", sym_file)
    dst = os.path.join(raw_dir, sym_file)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"Copied {sym_file} to raw directory.")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run(["C:/argo/venv/Scripts/python.exe", "scripts/prepare_v6_dataset.py", "--config", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_212042_v6_ASIAN_5m_AttentiveSniper_215\config.json", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] INJECT TENSORS INTO RUN DIRECTORY...", flush=True)
run_dir_tensors = r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_212042_v6_ASIAN_5m_AttentiveSniper_215/data/tensors"
os.makedirs(run_dir_tensors, exist_ok=True)
for f in os.listdir(root_tensors):
    if f.endswith(".npy") or f.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, f), os.path.join(run_dir_tensors, f))

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen(["C:/argo/venv/Scripts/python.exe", "-u", "src/training_v6/train_v6.py", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260519_212042_v6_ASIAN_5m_AttentiveSniper_215\config.json", "--run-id", "run_20260519_212042_v6_ASIAN_5m_AttentiveSniper_215", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
