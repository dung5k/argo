import paramiko
import sys

def fetch_logs():
    hostname = '160.187.146.149'
    port = 22
    username = 'root'
    password = 'Than1!chet'
    command = "journalctl -u aibot --since '1 hour ago' --no-pager && echo '--- STDERR ---' && tail -n 500 /opt/aibot/logs/stderr.log"

    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port, username, password, timeout=30)
        
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8', errors='replace')
        error_output = stderr.read().decode('utf-8', errors='replace')
        
        with open('prod_periodic_logs.txt', 'w', encoding='utf-8') as f:
            f.write(output)
            f.write("\n\n--- STDERR OUTPUT ---\n\n")
            f.write(error_output)
            
        print("Logs fetched successfully and saved to prod_periodic_logs.txt")
        client.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fetch_logs()
