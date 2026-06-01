import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

# 1. Kill old processes
client.exec_command('taskkill /F /IM python.exe /T')
client.exec_command('schtasks /end /tn "AgentTrainingXAG"')

# 2. Re-create argo2_xag.bat with correct Python interpreter
bat_content = """@echo off
cd /d "%~dp0"
C:\\argo\\venv\\Scripts\\python.exe -X utf8 autonomous_training_loop.py --symbol XAG --version v6
pause
"""
sftp = client.open_sftp()
with sftp.file('D:/DungLA/Argo/argo2_xag.bat', 'w') as f:
    f.write(bat_content)

# 3. Create data/raw folders and copy parquet files
cmd_powershell = """
$sessions = @('ASIAN', 'LONDON', 'NY')
foreach ($sess in $sessions) {
    $raw_dir = "D:\\DungLA\\Argo\\workspaces\\CFG_XAG_$($sess)_V6\\data\\raw"
    New-Item -Path $raw_dir -ItemType Directory -Force
    Copy-Item -Path "D:\\DungLA\\Argo\\workspaces\\CFG_CONFIG\\data\\raw\\*.parquet" -Destination $raw_dir -Force
}
"""
client.exec_command(f'powershell -Command "{cmd_powershell.replace("`", "``").replace("$", "`$")}"')

sftp.close()

# 4. Clear the bad run folders just in case
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\workspaces\\CFG_XAG_*\\runs -Recurse -Force -ErrorAction SilentlyContinue"')
client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\autonomous_training_xag.lockdir -Recurse -Force -ErrorAction SilentlyContinue"')

# 5. Restart the task
client.exec_command('schtasks /run /tn "AgentTrainingXAG"')

client.close()
