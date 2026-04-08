import os, subprocess, signal

out = subprocess.check_output(['wmic', 'process', 'get', 'processid,commandline'])
for line in out.decode('utf-8', errors='ignore').split('\n'):
    if 'trade_mt5.py' in line and 'python' in line.lower() and 'kill_bot' not in line:
        parts = line.strip().split()
        if not parts: continue
        try:
            pid = int(parts[-1])
            print(f"Killing PID: {pid}")
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            print("Error killing", line, e)
