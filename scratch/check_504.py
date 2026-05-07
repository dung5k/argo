import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('160.187.146.149', username='root', password='Than1!chet')
stdin, stdout, stderr = ssh.exec_command('journalctl -u aibot --since "3 hours ago" --no-pager | grep -i 504')
print('STDOUT:', stdout.read().decode())
print('STDERR:', stderr.read().decode())
ssh.close()
