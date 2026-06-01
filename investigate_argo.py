import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    client.connect('192.168.1.18', username='dungla', password='Than1!chet', timeout=10)
except Exception as e:
    print("SSH connect failed:", e)
    sys.exit(1)

print("=== CHECKING PYTHON PROCESSES ===")
stdin, stdout, stderr = client.exec_command('tasklist | findstr python')
print(stdout.read().decode('utf-8', errors='ignore'))

print("=== CHECKING LATEST LOGS ===")
# Find latest run
cmd_log = 'powershell -Command "$f = (Get-ChildItem \'D:\\DungLA\\Argo\\workspaces\\CFG_XAG_*\\runs\\*\\*.*\' -File | Sort-Object LastWriteTime -Descending | Select-Object -First 5); foreach ($file in $f) { Write-Host \\"LOG FILE: \\"$file.FullName; Get-Content $file.FullName -Tail 20 }"'
stdin, stdout, stderr = client.exec_command(cmd_log)
print('STDOUT:')
print(stdout.read().decode('utf-8', errors='ignore'))
print('STDERR:')
print(stderr.read().decode('utf-8', errors='ignore'))

client.close()
