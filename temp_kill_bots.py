import psutil
import os

for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if p.info['cmdline']:
            cmd = ' '.join(p.info['cmdline']).lower()
            if 'bot_v6.py' in cmd or 'bot_v3.py' in cmd:
                print(f"Killing bot process: PID={p.info['pid']}, CMD={cmd}")
                p.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
