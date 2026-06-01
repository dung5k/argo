import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

# Rewrite argo2_xag.bat
script = '@echo off\\ncd /d "%~dp0"\\npython autonomous_training_loop.py --symbol XAG --version v6\\npause'
cmd_write = f'powershell -Command "Set-Content -Path D:\\DungLA\\Argo\\argo2_xag.bat -Value \\\"{script}\\\""'
client.exec_command(cmd_write)

# Start schtasks
stdin, stdout, stderr = client.exec_command('schtasks /run /tn "AgentTrainingXAG"')
print('RUN STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RUN STDERR:', stderr.read().decode('utf-8', errors='ignore'))
client.close()
