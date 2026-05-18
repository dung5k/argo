import subprocess, os, sys
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260515_090924_v6_ASIAN_1m_LeadETH5m_182\config.json", "--run-id", "run_20260515_090924_v6_ASIAN_1m_LeadETH5m_182"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
