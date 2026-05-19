# -*- coding: utf-8 -*-
import subprocess
import os
import sys

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 1] RUNNING DATASET PREPARATION FOR XAG ASIAN V5...", flush=True)
sp1 = subprocess.run([
    "C:/argo/venv/Scripts/python.exe",
    "scripts/prepare_v3_dataset.py",
    "--config",
    "workspaces/CFG_XAG_ASIAN_V5/runs/run_20260518_163000_v5_asian_precision_flow_scalper/config.json",
    "--fast-hit-bars", "6",
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
    "workspaces/CFG_XAG_ASIAN_V5/runs/run_20260518_163000_v5_asian_precision_flow_scalper/config.json",
    "--run-id",
    "run_20260518_163000_v5_asian_precision_flow_scalper",
    "--scratch"
], stdout=open("bg_train_xag_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)

print(f"XAG V5 Training successfully started in the background. PID: {proc.pid}", flush=True)
