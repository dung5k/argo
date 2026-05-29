import paramiko
import sys
import os

ip = "192.167.1.18"
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
    client.connect(ip, username=user, password=password, timeout=10)
    print("Connected successfully with password.")
    
    commands = [
        "mkdir -p ~/.ssh",
        f"echo '{pub_key}' >> ~/.ssh/authorized_keys",
        "chmod 700 ~/.ssh",
        "chmod 600 ~/.ssh/authorized_keys"
    ]
    
    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd)
        err = stderr.read().decode('utf-8')
        if err:
            print(f"Error executing '{cmd}': {err}")
    
    print("SSH key deployed successfully!")

except Exception as e:
    print(f"Connection or execution failed: {e}")
finally:
    client.close()
