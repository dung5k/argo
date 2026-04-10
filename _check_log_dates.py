import os
import time

log_dir = "logs"
today_str = time.strftime('%Y-%m-%d')
print(f"Checking for logs modified today: {today_str}")

if not os.path.exists(log_dir):
    print("No logs directory found.")
else:
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    if not files:
        print("Logs directory is empty.")
    else:
        files.sort(key=os.path.getmtime, reverse=True)
        recent_files = files[:5]
        for f in recent_files:
            mtime = time.localtime(os.path.getmtime(f))
            print(f"- {f}: Modified at {time.strftime('%Y-%m-%d %H:%M:%S', mtime)}")
