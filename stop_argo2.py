import paramiko

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')

print("Stopping Scheduled Task AgentTrainingXAG...")
stdin, stdout, stderr = client.exec_command('schtasks /end /tn "AgentTrainingXAG"')
print("Task End Output:", stdout.read().decode('utf-8', errors='ignore'))
print("Task End Err:", stderr.read().decode('utf-8', errors='ignore'))

print("Killing all python processes...")
stdin, stdout, stderr = client.exec_command('taskkill /f /im python.exe')
print("Taskkill Output:", stdout.read().decode('utf-8', errors='ignore'))
print("Taskkill Err:", stderr.read().decode('utf-8', errors='ignore'))

client.close()
