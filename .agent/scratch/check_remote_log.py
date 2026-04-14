import os
import glob
import datetime
from pathlib import Path

def get_logs():
    log_dir = Path(os.environ.get("ARGO_LOGS_DIR", "C:/argo/logs"))
    today = datetime.date.today().isoformat()
    log_file = log_dir / f"tg_agent_{today}.log"
    if not log_file.exists():
        print(f"Log file not found: {log_file}")
        return
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print("\n".join(lines[-50:]))

get_logs()
