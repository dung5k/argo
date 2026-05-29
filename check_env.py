import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('192.168.1.18', username='dungla', timeout=5)
    stdin, stdout, stderr = client.exec_command('powershell -Command "Get-ChildItem Env: | Where-Object Name -match \'TELEGRAM|GEMINI|HUGGING|HF_\'"')
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    print("OUTPUT:")
    print(out)
    if err:
        print("ERROR:")
        print(err)
except Exception as e:
    print(f"Error: {e}")
