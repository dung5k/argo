import os
import subprocess
import paramiko
import time

def sync_to_node(host, user, pwd, remote_base, use_key=False):
    print(f"=== SYNCING TO {host} ===")
    
    # 1. Connect SSH to create directories
    print(f"Connecting to {host} to prepare directories...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if use_key:
            key_path = os.path.expanduser('~/.ssh/id_rsa')
            client.connect(host, username=user, key_filename=key_path, timeout=10)
        else:
            client.connect(host, username=user, password=pwd, timeout=10)
    except Exception as e:
        print(f"SSH Connection Failed to {host}: {e}")
        return False
        
    dirs_to_create = [
        f"{remote_base}/src/v8_engine",
        f"{remote_base}/v8_configs",
        f"{remote_base}/scripts",
        f"{remote_base}/data/v8_splits",
        f"{remote_base}/logs",
        f"{remote_base}/temp"
    ]
    
    for d in dirs_to_create:
        client.exec_command(f'powershell -Command "New-Item -ItemType Directory -Force -Path {d}"')
        
    client.close()
    time.sleep(1)
    print(f"Directories created on {host}.")
    
    # 2. SCP transfers
    folders_to_sync = [
        ("src\\v8_engine", f"{remote_base}/src"),
        ("v8_configs", f"{remote_base}"),
        ("data\\v8_splits", f"{remote_base}/data")
    ]
    
    for local_f, remote_f in folders_to_sync:
        if os.path.exists(local_f):
            print(f"Syncing {local_f} to {remote_f}...")
            subprocess.run(["scp", "-r", local_f, f"{user}@{host}:{remote_f}"])
        else:
            print(f"Warning: Local folder {local_f} does not exist.")
            
    v8_scripts = [f for f in os.listdir("scripts") if f.startswith("v8_") and f.endswith(".py")]
    for script in v8_scripts:
        print(f"Syncing scripts\\{script}...")
        subprocess.run(["scp", f"scripts\\{script}", f"{user}@{host}:{remote_base}/scripts/"])
        
    print(f"=== SYNC COMPLETE FOR {host} ===")
    return True

def run_sync():
    print("=== STARTING CLUSTER SYNC ===")
    remote_base = 'D:/DungLA/Argo'
    
    # Sync ARGO2
    sync_to_node('192.168.1.18', 'dungla', 'Than1!chet', remote_base, use_key=False)
    
    # Sync ARGO3
    sync_to_node('192.168.1.16', 'dungla', 'Than1!chet', remote_base, use_key=True)

if __name__ == "__main__":
    run_sync()
