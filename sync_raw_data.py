import os
import subprocess

sessions = ['ASIAN', 'LONDON', 'NY', 'WEEKEND']
for s in sessions:
    src_dir = f"d:\\DungLA\\client1\\workspaces\\CFG_LTC_{s}_V6\\data\\raw"
    if os.path.exists(src_dir):
        print(f"Syncing {src_dir} to Argo2...")
        # Create remote dir
        subprocess.run(["ssh", "dungla@192.168.1.18", f"mkdir -p d:\\DungLA\\Argo\\workspaces\\CFG_LTC_{s}_V6\\data"])
        # SCP
        subprocess.run(["scp", "-r", src_dir, f"dungla@192.168.1.18:d:\\DungLA\\Argo\\workspaces\\CFG_LTC_{s}_V6\\data\\"])
        print(f"Done syncing {s}")
