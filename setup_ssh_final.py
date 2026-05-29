import paramiko
import sys
import os
import time
import socket

ip = "192.167.1.18"
user = "dungla"
password = "Than1!chet"

def check_port(host, port, timeout=5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

print(f"Checking if port 22 is open on {ip}...")
if not check_port(ip, 22):
    print(f"Error: Port 22 is closed on {ip}. Host might be down or blocked by firewall.")
    sys.exit(1)
print(f"Port 22 is open.")

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
    
    commands = [
        "mkdir -p ~/.ssh",
        f"echo '{pub_key}' >> ~/.ssh/authorized_keys",
        "chmod 700 ~/.ssh",
        "chmod 600 ~/.ssh/authorized_keys"
    ]
    
    for cmd in commands:
        print(f"Executing: {cmd[:30]}...")
        stdin, stdout, stderr = client.exec_command(cmd)
        err = stderr.read().decode('utf-8')
        if err:
            print(f"Error executing '{cmd}': {err}")
    
    print("SSH key deployed successfully!")

except Exception as e:
    print(f"Connection or execution failed: {e}")
finally:
    client.close()
