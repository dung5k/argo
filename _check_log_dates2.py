import os
import time

log_dir = os.path.join("clientGH", "logs")
print(f"Checking for logs in: {log_dir}")
today_str = time.strftime('%Y-%m-%d')

if not os.path.exists(log_dir):
    print(f"No logs directory found at {log_dir}")
else:
    files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if os.path.isfile(os.path.join(log_dir, f))]
    if not files:
        print("Logs directory is empty.")
    else:
        files.sort(key=os.path.getmtime, reverse=True)
        recent_files = files[:3]
        for f in recent_files:
            mtime = time.localtime(os.path.getmtime(f))
            print(f"- {f}: Modified at {time.strftime('%Y-%m-%d %H:%M:%S', mtime)}")
        
        # In the very latest file contents
        latest = files[0]
        print(f"\n--- Latest file: {latest} ---")
        try:
            with open(latest, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                for line in lines[-20:]:  # Last 20 lines
                    print(line.strip())
        except Exception as e:
            print(f"Error reading: {e}")
