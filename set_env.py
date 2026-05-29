import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('192.168.1.18', username='dungla', timeout=5)
    
    ps_cmd = """powershell -Command "[Environment]::SetEnvironmentVariable('HF_HOME', 'D:\HuggingFaceCache', 'User'); [Environment]::SetEnvironmentVariable('HF_REPO_ID', 'dung5k/argo_workspaces', 'User'); [Environment]::SetEnvironmentVariable('HF_TOKEN', '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', 'User')" """
    
    stdin, stdout, stderr = client.exec_command(ps_cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print("OUTPUT:", out)
    print("ERROR:", err)
except Exception as e:
    print(f"Error: {e}")
