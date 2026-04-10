import os
import time
import glob

print("Checking bot logs in 'logs' folder...")
log_dir = "logs"
if not os.path.exists(log_dir):
    print("No logs directory found.")
else:
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    files.sort(key=os.path.getmtime, reverse=True)
    if not files:
        print("Logs directory is empty.")
    else:
        latest = files[0]
        mtime = time.localtime(os.path.getmtime(latest))
        print(f"Latest log file: {latest} (Modified: {time.strftime('%Y-%m-%d %H:%M:%S', mtime)})")
        with open(latest, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            print("--- Beginning of latest output snippet ---")
            for line in lines[-30:]:
                print(line.strip())
            print("--- End of latest output snippet ---")
