import os, glob
from pathlib import Path

# Tim train.log trong thu muc runs moi nhat
argo_logs = os.environ.get("ARGO_LOGS_DIR", "")
if not argo_logs:
    base = Path(__file__).resolve().parent.parent.parent
    argo_logs = str(base / "logs")

runs_dir = Path(argo_logs) / "runs"
print(f"[DUMP] Searching runs in: {runs_dir}")

# Tim tat ca train.log, sort theo mtime
pattern = str(runs_dir / "**" / "train.log")
files = sorted(glob.glob(pattern, recursive=True), key=os.path.getmtime, reverse=True)

if not files:
    print(f"[DUMP] Khong tim thay train.log. Thu tim trong C:/argo/logs/runs/...")
    files = sorted(glob.glob("C:/argo/logs/runs/**/train.log", recursive=True), key=os.path.getmtime, reverse=True)

if not files:
    print("[DUMP] Van khong tim thay train.log")
else:
    log_file = files[0]
    print(f"[DUMP] File: {log_file}")
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"[DUMP] Tong dong: {len(lines)}")
    # In 40 dong sau CURRICULUM
    for i, l in enumerate(lines):
        if "CURRICULUM" in l or "Epoch" in l:
            start = max(0, i-1)
            end = min(len(lines), i+30)
            for ll in lines[start:end]:
                print(ll.rstrip())
            break
    else:
        # In 40 dong cuoi
        for l in lines[-40:]:
            print(l.rstrip())
