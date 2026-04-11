import os, glob
from pathlib import Path

argo_logs = os.environ.get("ARGO_LOGS_DIR", "")
if not argo_logs:
    base = Path(__file__).resolve().parent.parent.parent
    argo_logs = str(base / "logs")

runs_dir = Path(argo_logs) / "runs"
print(f"[DUMP] Searching runs in: {runs_dir}")

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
    # In 100 dòng đầu và 100 dòng cuối để bắt toàn trạng
    if len(lines) > 200:
        for l in lines[:100]:
            print(l.rstrip())
        print("\n... [TRUNCATED] ...\n")
        for l in lines[-100:]:
            print(l.rstrip())
    else:
        for l in lines:
            print(l.rstrip())
