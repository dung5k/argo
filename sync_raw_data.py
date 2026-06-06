import os
import subprocess

sessions = ['ASIAN', 'LONDON', 'NY', 'WEEKEND']
for s in sessions:
    src_dir = f"d:\\DungLA\\client1\\workspaces\\CFG_XAG_{s}_V6\\data\\raw"
    if os.path.exists(src_dir):
        print(f"Syncing {src_dir} to Argo2...")
        # Create remote dir using powershell since Argo2 is Windows
        subprocess.run(["ssh", "dungla@192.168.1.18", f"powershell -Command \"New-Item -ItemType Directory -Force -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_{s}_V6\\data\""])
        # SCP
        subprocess.run(["scp", "-r", src_dir, f"dungla@192.168.1.18:D:/DungLA/Argo/workspaces/CFG_XAG_{s}_V6/data/"])
        print(f"Done syncing {s}")
