# -*- coding: utf-8 -*-
import os
import glob
import time
import subprocess as sp
from huggingface_hub import HfApi

print("1. Deleting leftover tf1, tf2 tensors locally...")
local_tensor_dir = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "data", "tensors")
for f in glob.glob(os.path.join(local_tensor_dir, "X_tensor_*_tf1.npy")):
    os.remove(f)
for f in glob.glob(os.path.join(local_tensor_dir, "X_tensor_*_tf2.npy")):
    os.remove(f)

print("2. Deleting leftover tf1, tf2 tensors on HuggingFace...")
hf_token = os.environ.get("HF_TOKEN", "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")
api = HfApi(token=hf_token)
repo_id = "dung5k/argo_workspaces"
prefix = "workspaces/CFG_LTC_ASIAN_V6/data/tensors/"
try:
    files_to_delete = []
    all_files = api.list_repo_files(repo_id=repo_id, repo_type="dataset")
    for f in all_files:
        if f.startswith(prefix) and ("tf1.npy" in f or "tf2.npy" in f):
            files_to_delete.append(f)
    if files_to_delete:
        api.delete_files(paths=files_to_delete, repo_id=repo_id, repo_type="dataset", commit_message="Remove old ASIAN mtf tensors")
        print("Deleted on HF:", files_to_delete)
except Exception as e:
    print("HF delete error:", e)

print("3. Relaunching ASIAN training...")
# Kill the crashed train_v6 process if it somehow is still alive (it already exited though)
# Rerun generation to be safe
run_id = "run_20260514_151806_v6_ASIAN_15m_TP5_SL25_BigBrain_75"
config_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id, "config.json")
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Generating new dataset tensors for ASIAN...")
with open("upload_v6_asian.log", "w", encoding="utf-8") as f_log:
    sp1 = sp.run(["python", "scripts/prepare_v6_dataset.py", "--config", config_path], env=env, stdout=f_log, stderr=sp.STDOUT)
if sp1.returncode != 0:
    print("Error generating dataset, check upload_v6_asian.log")
    exit(1)

print("Dataset generation completed. Starting training...")
proc = sp.Popen(["python", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=sp.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
