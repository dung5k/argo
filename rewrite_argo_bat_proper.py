import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

script = """@echo off
cd /d "%~dp0"
python autonomous_training_loop.py --symbol XAG --version v6
pause
"""

sftp = client.open_sftp()
with sftp.file('D:/DungLA/Argo/argo2_xag.bat', 'w') as f:
    f.write(script)
sftp.close()

# Start schtasks
stdin, stdout, stderr = client.exec_command('schtasks /run /tn "AgentTrainingXAG"')
print('RUN STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RUN STDERR:', stderr.read().decode('utf-8', errors='ignore'))
client.close()
