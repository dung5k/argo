import glob
import os

files = glob.glob('d:/DungLA/Argo/workspaces/CFG_LTC*/*/*/prepare_dataset.log')
if not files:
    print("No logs found")
else:
    latest = max(files, key=os.path.getmtime)
    print(f"Latest log: {latest}")
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Lines count: {len(lines)}")
            if len(lines) > 0:
                print("".join(lines[-30:]))
    except Exception as e:
        print(f"Error reading {latest}: {e}")
