import subprocess, os, sys
run_id = "run_20260514_145822_v6_LONDON_15m_TP6_SL3_Drop30_W30_FarmSeed109"
config_path = r"workspaces\CFG_LTC_LONDON_V6\runs\run_20260514_145822_v6_LONDON_15m_TP6_SL3_Drop30_W30_FarmSeed109\config.json"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Generating new dataset tensors...")
with open("upload_v6.log", "w", encoding="utf-8") as f_log:
    sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", config_path, "--no-upload"], env=env, stdout=f_log, stderr=subprocess.STDOUT)
if sp1.returncode != 0:
    print("Error generating dataset, check upload_v6.log")
    sys.exit(1)
print("Dataset generation completed. Starting training...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
