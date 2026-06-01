import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')
stdin, stdout, stderr = client.exec_command('schtasks /run /tn \\AgentTrainingXAG')
print('RUN STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
print('RUN STDERR:', stderr.read().decode('utf-8', errors='ignore'))
client.close()
