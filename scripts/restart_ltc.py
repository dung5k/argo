import subprocess
import os
import psutil

# Find and kill old bot_v6 processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
            if 'src\\bot_v6\\bot_v6.py' in ' '.join(proc.info['cmdline']) or 'src/bot_v6/bot_v6.py' in ' '.join(proc.info['cmdline']):
                print(f"Killing old bot PID: {proc.info['pid']}")
                proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass

# Start new bot
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
cmd = [r"C:\argo\venv\Scripts\python.exe", "-u", "src/bot_v6/bot_v6.py", "bot_config_v6_ltc.json", "bot_schedule_v6_ltc.json"]
p2 = subprocess.Popen(
    cmd, 
    stdout=open("ltc_bot.log", "a", encoding="utf-8"), 
    stderr=subprocess.STDOUT, 
    env=env,
    creationflags=0x00000008  # DETACHED_PROCESS to survive shell closure
)
print(f"Started new LTC Bot PID: {p2.pid}")
