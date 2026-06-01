import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

print("1. Stopping training on ARGO2 (killing python and cmd)...")
client.exec_command('taskkill /F /IM python.exe /T')
client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'cmd.exe\'\\" | Where-Object {$_.CommandLine -match \'argo2_xag.bat\'} | Invoke-CimMethod -MethodName Terminate"')
client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'cmd.exe\'\\" | Where-Object {$_.CommandLine -match \'autonomous_training_loop\'} | Invoke-CimMethod -MethodName Terminate"')

print("2. Pulling latest code on ARGO2...")
# Using git pull in the D:\DungLA\Argo directory
stdin, stdout, stderr = client.exec_command('cd /d D:\\DungLA\\Argo && git pull origin main')
print('GIT PULL STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('GIT PULL STDERR:', stderr.read().decode('utf-8', errors='ignore'))

print("3. Deleting all results (workspaces & lock files)...")
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_* -Recurse -Force -ErrorAction SilentlyContinue"')
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\autonomous_training_xag.lockdir -Recurse -Force -ErrorAction SilentlyContinue"')

print("4. Restarting training on ARGO2...")
stdin, stdout, stderr = client.exec_command('schtasks /run /tn "AgentTrainingXAG"')
print('RESTART STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RESTART STDERR:', stderr.read().decode('utf-8', errors='ignore'))

client.close()
