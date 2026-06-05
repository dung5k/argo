import os
import glob
import subprocess

print("--- RECENT TEMP LOGS ---")
log_files = glob.glob(r"D:\DungLA\Argo\temp\*.log")
if log_files:
    latest_logs = sorted(log_files, key=os.path.getmtime, reverse=True)[:3]
    for log in latest_logs:
        print(f"\n--- {log} ---")
        try:
            with open(log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("".join(lines[-20:]))
        except Exception as e:
            print(f"Error reading {log}: {e}")
else:
    print("No temp log files found")

print("\n--- RUNNING PYTHON PROCESSES ---")
try:
    output = subprocess.check_output('wmic process where "name=\'python.exe\'" get processid, commandline', shell=True).decode()
    print(output)
except Exception as e:
    print(e)
