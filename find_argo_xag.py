import paramiko
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.18', username='dungla', password='Than1!chet')
stdin, stdout, stderr = client.exec_command('powershell -Command "Get-ChildItem D:\\DungLA\\Argo -Recurse -Filter *XAG*.parquet | Select-Object FullName"')
print('STDOUT:', stdout.read().decode('utf-8', errors='ignore'))
client.close()
