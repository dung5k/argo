import paramiko
import sys
import os
import time

ip = "192.168.1.18"
user = "dungla"
password = "Than1!chet"

try:
    with open(os.path.expanduser("~/.ssh/id_rsa.pub"), "r") as f:
        pub_key = f.read().strip()
except Exception as e:
    print(f"Failed to read public key: {e}")
    sys.exit(1)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {user}@{ip}...")
    client.connect(ip, username=user, password=password, timeout=15)
    print("Connected successfully with password.")
    
    # Fix icacls command quoting issue
    ps_command = f"""powershell -Command "$key='{pub_key}'; Add-Content -Force -Path $env:ProgramData\\ssh\\administrators_authorized_keys -Value $key; icacls.exe $env:ProgramData\\ssh\\administrators_authorized_keys /inheritance:r /grant Administrators:F /grant SYSTEM:F" """
    
    print("Executing permission script...")
    stdin, stdout, stderr = client.exec_command(ps_command)
    err = stderr.read().decode('utf-8')
    out = stdout.read().decode('utf-8')
    
    if out: print(f"Output: {out}")
    if err: print(f"Error: {err}")
    
    print("SSH key deployed to administrators_authorized_keys successfully!")

except Exception as e:
    print(f"Connection or execution failed: {e}")
finally:
    client.close()
