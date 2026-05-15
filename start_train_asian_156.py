import subprocess, os, sys
run_id = "run_20260515_021934_v6_ASIAN_5m_TP5_SL25_BigBrain_156"
config_path = r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260515_021934_v6_ASIAN_5m_TP5_SL25_BigBrain_156\config.json"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Generating new tensors for 5m Timeframe...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
