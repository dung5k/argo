import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

# 1. Kill old training task first to release any locks
client.exec_command('schtasks /end /tn "AgentTrainingXAG"')

# 2. Write pull script
pull_script = '@echo off\\ncd /d D:\\DungLA\\Argo\\ngit pull origin main > git_pull_log.txt 2>&1\\n'
sftp = client.open_sftp()
with sftp.file('D:/DungLA/Argo/pull_code.bat', 'w') as f:
    f.write(pull_script)
sftp.close()

# 3. Create and run pull task
cmd_create = 'schtasks /create /tn "AgentPull" /tr "D:\\DungLA\\Argo\\pull_code.bat" /sc once /st 00:00 /ru "dungla" /rp "Than1!chet" /f'
client.exec_command(cmd_create)
client.exec_command('schtasks /run /tn "AgentPull"')

time.sleep(5) # wait for git pull to finish

# 4. Read git pull log
stdin, stdout, stderr = client.exec_command('type D:\\DungLA\\Argo\\git_pull_log.txt')
print('GIT PULL LOG:')
print(stdout.read().decode('utf-8', errors='ignore'))

# 5. Restart training
client.exec_command('schtasks /run /tn "AgentTrainingXAG"')

client.close()
