import paramiko
import os
import glob

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

print("1. Killing python and cmd on ARGO2...")
client.exec_command('taskkill /F /IM python.exe /T')
client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'cmd.exe\'\\" | Where-Object {$_.CommandLine -match \'argo2_xag.bat\'} | Invoke-CimMethod -MethodName Terminate"')
client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'cmd.exe\'\\" | Where-Object {$_.CommandLine -match \'autonomous_training_loop\'} | Invoke-CimMethod -MethodName Terminate"')

print("2. Copying code to ARGO2...")
sftp = client.open_sftp()
def put_file(local_path, remote_path):
    try:
        sftp.stat(os.path.dirname(remote_path))
    except FileNotFoundError:
        # Create remote dir if not exists. Simple approach since we only go 1 level deep mostly
        try:
            client.exec_command(f'mkdir "{os.path.dirname(remote_path)}"')
        except:
            pass
    sftp.put(local_path, remote_path)

# Copy root python files
for f in glob.glob("*.py"):
    if os.path.isfile(f):
        put_file(f, f"D:/DungLA/Argo/{f}")

# Copy scripts folder
client.exec_command('mkdir D:\\DungLA\\Argo\\scripts')
for f in glob.glob("scripts/*.py"):
    if os.path.isfile(f):
        put_file(f, f"D:/DungLA/Argo/{f.replace(chr(92), '/')}")

# Copy src folder recursively
client.exec_command('powershell -Command "New-Item -Path D:\\DungLA\\Argo\\src -ItemType Directory -Force"')
for root, dirs, files in os.walk("src"):
    for file in files:
        if file.endswith(".py"):
            local_path = os.path.join(root, file)
            remote_path = f"D:/DungLA/Argo/{local_path.replace(chr(92), '/')}"
            try:
                sftp.stat(os.path.dirname(remote_path))
            except FileNotFoundError:
                client.exec_command(f'powershell -Command "New-Item -Path {os.path.dirname(remote_path)} -ItemType Directory -Force"')
            put_file(local_path, remote_path)

sftp.close()

print("3. Wiping workspaces and AI history on ARGO2...")
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_* -Recurse -Force -ErrorAction SilentlyContinue"')
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\ai_decision_history_XAG.json -Force -ErrorAction SilentlyContinue"')
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\.agent\\strategy_prompt_XAG.md -Force -ErrorAction SilentlyContinue"')
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\autonomous_training_xag.lockdir -Recurse -Force -ErrorAction SilentlyContinue"')

print("3.5 Recreating raw data directories to prevent FileNotFoundError...")
client.exec_command('powershell -Command "New-Item -ItemType Directory -Force -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_ASIAN_V6\\data\\raw"')
client.exec_command('powershell -Command "New-Item -ItemType Directory -Force -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_LONDON_V6\\data\\raw"')
client.exec_command('powershell -Command "New-Item -ItemType Directory -Force -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_NY_V6\\data\\raw"')
client.exec_command('powershell -Command "New-Item -ItemType Directory -Force -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_WEEKEND_V6\\data\\raw"')

print("4. Updating XAG configs to 1m timeframe...")
script_fix_configs = """import glob, json
for f in glob.glob('D:/DungLA/Argo/bot_config_v6_xag_*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('"5min"', '"1m"').replace('"M15"', '"M1"')
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
"""
sftp = client.open_sftp()
with sftp.file('D:/DungLA/Argo/fix_configs.py', 'w') as f:
    f.write(script_fix_configs)
sftp.close()
client.exec_command('python D:/DungLA/Argo/fix_configs.py')

print("5. Starting training on ARGO2...")
stdin, stdout, stderr = client.exec_command('schtasks /run /tn "AgentTrainingXAG"')
print('RESTART STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RESTART STDERR:', stderr.read().decode('utf-8', errors='ignore'))

client.close()
