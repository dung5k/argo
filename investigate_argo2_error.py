import paramiko
import sys

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

print("Checking latest training loop logs...")
stdin, stdout, stderr = client.exec_command('powershell -Command "Get-Content D:\\DungLA\\Argo\\train_startup.log -Tail 30"')
print("--- train_startup.log ---")
print(stdout.read().decode('utf-8', errors='ignore'))

print("Checking latest prepare_dataset.log...")
stdin, stdout, stderr = client.exec_command('powershell -Command "$f = (Get-ChildItem \'D:\\DungLA\\Argo\\workspaces\\CFG_XAG_*\\runs\\*\\prepare_dataset.log\' | Sort-Object LastWriteTime -Descending | Select-Object -First 1); if ($f) { Get-Content $f.FullName -Tail 20 } else { echo \'No log found\' }"')
print("--- prepare_dataset.log ---")
print(stdout.read().decode('utf-8', errors='ignore'))

print("Checking latest train_v6.log...")
stdin, stdout, stderr = client.exec_command('powershell -Command "$f = (Get-ChildItem \'D:\\DungLA\\Argo\\workspaces\\CFG_XAG_*\\runs\\*\\train_v6.log\' | Sort-Object LastWriteTime -Descending | Select-Object -First 1); if ($f) { Get-Content $f.FullName -Tail 20 } else { echo \'No log found\' }"')
print("--- train_v6.log ---")
print(stdout.read().decode('utf-8', errors='ignore'))

client.close()
