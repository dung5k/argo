import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')
cmd_create = 'schtasks /create /tn "AgentTrainingXAG" /tr "D:\\DungLA\\Argo\\argo2_xag.bat" /sc once /st 00:00 /ru "dungla" /rp "Than1!chet" /f'
cmd_run = 'schtasks /run /tn "AgentTrainingXAG"'
stdin, stdout, stderr = client.exec_command(cmd_create)
print('CREATE STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('CREATE STDERR:', stderr.read().decode('utf-8', errors='ignore'))

stdin, stdout, stderr = client.exec_command(cmd_run)
print('RUN STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RUN STDERR:', stderr.read().decode('utf-8', errors='ignore'))

client.close()
