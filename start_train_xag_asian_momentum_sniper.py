# -*- coding: utf-8 -*-
import subprocess
import os
import sys

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 1] RUNNING DATASET PREPARATION FOR XAG ASIAN V5 (FHB=4)...", flush=True)
sp1 = subprocess.run([
    "C:/argo/venv/Scripts/python.exe",
    "scripts/prepare_v3_dataset.py",
    "--config",
    "workspaces/CFG_XAG_ASIAN_V5/runs/run_20260519_213832_v5_asian_momentum_sniper/config.json",
    "--fast-hit-bars", "4",
    "--no-upload",
    "--monthly-split"
], env=env)

if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v3_dataset failed!", flush=True)
    sys.exit(1)

print(">>> [PHASE 2] LAUNCHING TRAINING ON GPU CUDA...", flush=True)
proc = subprocess.Popen([
    "C:/argo/venv/Scripts/python.exe",
    "-u",
    "src/training_v3/train_v3.py",
    "workspaces/CFG_XAG_ASIAN_V5/runs/run_20260519_213832_v5_asian_momentum_sniper/config.json",
    "--run-id",
    "run_20260519_213832_v5_asian_momentum_sniper",
    "--scratch"
], stdout=open("bg_train_xag_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)

print(f"XAG V5 Training successfully started in the background. PID: {proc.pid}", flush=True)
