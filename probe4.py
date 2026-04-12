import os, sys, glob
print("=== PROBE 4 ===")
try:
    log_dir = os.environ.get("ARGO_LOGS_DIR", "logs")
    print(f"ARGO_LOGS_DIR: {log_dir}")
    unified = os.path.join(log_dir, "clientV2_unified.log")
    
    runs_dir = os.path.join(log_dir, "runs")
    print(f"RUNS FOLDER: {runs_dir}")
    if os.path.exists(runs_dir):
        print(f"Folders in runs: {os.listdir(runs_dir)}")
    else:
        print("RUNS FOLDER DOES NOT EXIST.")

    print("\n--- LAST 30 LINES OF UNIFIED LOG ---")
    if os.path.exists(unified):
        with open(unified, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            print("".join(lines[-30:]))
    else:
        print("UNIFIED LOG NOT FOUND.")
except Exception as e:
    print(f"ERROR: {e}")
