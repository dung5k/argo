import paramiko

script = """import glob, json
for f in glob.glob('D:/DungLA/Argo/bot_config_v6_xag_*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('"5min"', '"1m"').replace('"M15"', '"M1"')
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print('Updated ' + f)
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

sftp = client.open_sftp()
with sftp.file('D:/DungLA/Argo/fix_configs.py', 'w') as f:
    f.write(script)
sftp.close()

print("Fixing configs...")
stdin, stdout, stderr = client.exec_command('python D:/DungLA/Argo/fix_configs.py')
print('STDOUT:', stdout.read().decode('utf-8'))
print('STDERR:', stderr.read().decode('utf-8'))

print("Deleting old workspaces...")
stdin, stdout, stderr = client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_* -Recurse -Force -ErrorAction SilentlyContinue"')
print('STDOUT:', stdout.read().decode('utf-8'))
print('STDERR:', stderr.read().decode('utf-8'))

print("Deleting lock files...")
stdin, stdout, stderr = client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\autonomous_training_xag.lockdir -Recurse -Force -ErrorAction SilentlyContinue"')
print('STDOUT:', stdout.read().decode('utf-8'))
print('STDERR:', stderr.read().decode('utf-8'))

print("Killing old python processes...")
stdin, stdout, stderr = client.exec_command('taskkill /F /IM python.exe /T')
print('STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('STDERR:', stderr.read().decode('utf-8', errors='ignore'))

print("Killing old cmd processes...")
stdin, stdout, stderr = client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\\"Name=\'cmd.exe\'\\\" | Where-Object {$_.CommandLine -match \'argo2_xag.bat\'} | Invoke-CimMethod -MethodName Terminate"')
print('STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('STDERR:', stderr.read().decode('utf-8', errors='ignore'))

print("Starting argo2_xag.bat via schtasks...")
cmd_schtasks = 'schtasks /create /tn "AgentTrainingXAG" /tr "D:\\DungLA\\Argo\\argo2_xag.bat" /sc once /st 00:00 /ru "dungla" /rp "Than1!chet" /it /f ; schtasks /run /tn "AgentTrainingXAG"'
stdin, stdout, stderr = client.exec_command(f'powershell -Command "{cmd_schtasks}"')
print('STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('STDERR:', stderr.read().decode('utf-8', errors='ignore'))

client.close()
