import sys
import paramiko
import os
import subprocess

def run():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect('160.187.146.149', username='root', password='Than1!chet')
        stdin, stdout, stderr = client.exec_command('journalctl -u aibot --since "1 hour ago" --no-pager && echo "--- STDERR ---" && tail -n 500 /opt/aibot/logs/stderr.log')
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
    except Exception as e:
        with open(r'd:\DungLA\aibot\periodic_task_error.log', 'a', encoding='utf-8') as f:
            f.write(f"SSH failed: {e}\n")
        return
    finally:
        client.close()
        
    lines = (output + "\n" + error).split('\n')
    errors_found = []
    
    for idx, line in enumerate(lines):
        if "spreadsheetId" in line or "Missing required parameters: spreadsheetId" in line:
            continue
        if "AUTH_FAIL" in line:
            continue
            
        is_error = False
        error_type = ""
        
        if "Connection terminated" in line or "timeout" in line.lower() or "DATABASE_ERROR" in line:
            is_error = True
            error_type = "Database Error"
            
        if "OpenRouter API error 404" in line or "deprecated" in line.lower():
            is_error = True
            error_type = "AI Model Error"
            
        if "FATAL" in line or "Traceback" in line or "Exception" in line:
            is_error = True
            error_type = "System Crash/Exception"
            
        if is_error:
            errors_found.append(f"- [{error_type}] {line.strip()[:200]}")
            
    unique_errors = list(dict.fromkeys(errors_found))
    
    if not unique_errors:
        print("[OK] No issues found")
        # Run empty done so the extension knows it's finished
        subprocess.run(['python', '.agent/send_to_tele.py', ' ', '--done'])
    else:
        summary = "🚨 **PERIODIC LOG AUDIT ALERT** 🚨\n\n"
        for err in unique_errors[:15]:
            summary += err + "\n"
        
        with open('error_summary.txt', 'w', encoding='utf-8') as f:
            f.write(summary)
            
        wrapper = """import sys
import os
os.environ["TELEGRAM_BOT_TOKEN"] = "8057292338:AAF2EnD_V9dWVNiDPnEfPEyYMKHxJQnNzlg"
with open('error_summary.txt', 'r', encoding='utf-8') as f:
    content = f.read()
sys.path.insert(0, os.path.abspath('.agent'))
import send_to_tele
send_to_tele.send_to_telegram(content, is_done=True, target_channels='1816854047')
"""
        with open('send_wrapper.py', 'w', encoding='utf-8') as f:
            f.write(wrapper)
        
        subprocess.run(['python', 'send_wrapper.py'])

if __name__ == '__main__':
    run()
