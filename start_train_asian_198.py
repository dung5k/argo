import subprocess, os, sys
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260515_121732_v6_ASIAN_1m_TrueDataset_LeadBTC_198\config.json", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260515_121732_v6_ASIAN_1m_TrueDataset_LeadBTC_198\config.json", "--run-id", "run_20260515_121732_v6_ASIAN_1m_TrueDataset_LeadBTC_198"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
