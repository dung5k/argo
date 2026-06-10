import os
import paramiko
import time

def sftp_put_dir(sftp, local_dir, remote_dir):
    """Recursively uploads a directory to remote server via SFTP"""
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass # Already exists
        
    for item in os.listdir(local_dir):
        local_path = os.path.join(local_dir, item)
        # Use forward slashes for MT5/Windows remote paths
        remote_path = f"{remote_dir}/{item}".replace("\\", "/")
        
        if os.path.isdir(local_path):
            if item in ['.git', '__pycache__', 'temp_argo', '.antigravity_env']:
                continue
            sftp_put_dir(sftp, local_path, remote_path)
        else:
            # Skip heavy binaries or cache
            if item.endswith('.pyc') or item.endswith('.log') or item.endswith('.bat') and 'auto' in item:
                continue
            try:
                sftp.put(local_path, remote_path)
            except Exception as e:
                print(f"Failed to upload {local_path}: {e}")

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
        
    time.sleep(1)
    print(f"Directories created on {host}. Opening SFTP client...")
    
    sftp = client.open_sftp()
    
    # 2. SFTP transfers
    folders_to_sync = [
        ("src/v8_engine", f"{remote_base}/src/v8_engine"),
        ("v8_configs", f"{remote_base}/v8_configs"),
        ("data/v8_splits", f"{remote_base}/data/v8_splits")
    ]
    
    for local_f, remote_f in folders_to_sync:
        if os.path.exists(local_f):
            print(f"Syncing {local_f} to {remote_f}...")
            sftp_put_dir(sftp, local_f, remote_f)
        else:
            print(f"Warning: Local folder {local_f} does not exist.")
            
    # Sync python scripts
    print(f"Syncing script folder...")
    try:
        sftp.mkdir(f"{remote_base}/scripts")
    except IOError:
        pass
        
    v8_scripts = [f for f in os.listdir("scripts") if f.startswith("v8_") and f.endswith(".py")]
    for script in v8_scripts:
        local_p = os.path.join("scripts", script)
        remote_p = f"{remote_base}/scripts/{script}"
        sftp.put(local_p, remote_p)
        
    sftp.close()
    client.close()
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
