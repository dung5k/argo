import os
import sys
import psutil
import subprocess
import time
from datetime import datetime

# Configure environment if needed
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# --- CONFIGURATION ---
ARGO2_IP = "192.168.1.18"
ARGO2_USER = "dungla"
TELEGRAM_SCRIPT = ".agent/send_to_tele.py"
TELEGRAM_CHANNEL = "1816854047"
PYTHON_EXE = sys.executable

def send_tele_alert(message):
    try:
        subprocess.run([PYTHON_EXE, TELEGRAM_SCRIPT, message, "--channel", TELEGRAM_CHANNEL], check=True)
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

def check_local_running():
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            if p.info['name'] and 'python.exe' in p.info['name'].lower():
                cmdline = p.info['cmdline']
                if cmdline and 'autonomous_training_loop.py' in ' '.join(cmdline):
                    return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def restart_local():
    print("Local process is down! Restarting via schtasks...")
    script_path = os.path.abspath("START_TRAINING.bat")
    
    # 1. Get current username in domain\user format
    username = os.environ.get('USERDOMAIN', '') + '\\' + os.environ.get('USERNAME', '')
    
    # 2. Create interactive task to bypass Session 0 restrictions
    create_cmd = f'schtasks /create /tn "Client1_LTC_Training" /tr "{script_path}" /sc once /st 00:00 /ru "{username}" /it /f'
    try:
        subprocess.run(create_cmd, shell=True, check=True)
        # 3. Run the task
        subprocess.run('schtasks /run /tn "Client1_LTC_Training"', shell=True, check=True)
        send_tele_alert("🚨 CẢNH BÁO TỪ HỆ THỐNG GIÁM SÁT: Tiến trình training LTC trên máy Client1 đã bị tắt/crash. Đã tự động kích hoạt cứu hộ và khởi động lại thành công!")
        return True
    except Exception as e:
        error_msg = f"❌ LỖI CỨU HỘ MÁY CLIENT1: Không thể khởi động lại LTC training. Lỗi: {e}"
        print(error_msg)
        send_tele_alert(error_msg)
        return False

def check_argo2_running():
    try:
        # Check if python is running on argo2 by fetching full tasklist
        result = subprocess.run(
            ['ssh', f'{ARGO2_USER}@{ARGO2_IP}', 'tasklist'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0 and 'python.exe' in result.stdout.lower():
            return True
        return False
    except Exception as e:
        print(f"Error checking Argo2: {e}")
        return False

def restart_argo2():
    print("Argo2 process is down! Restarting via schtasks...")
    try:
        result = subprocess.run(
            ['ssh', f'{ARGO2_USER}@{ARGO2_IP}', "schtasks /run /tn 'Argo2_XAG_Training'"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            send_tele_alert("🚨 CẢNH BÁO TỪ HỆ THỐNG GIÁM SÁT: Tiến trình training XAG trên máy Argo2 đã bị tắt/crash. Đã tự động phát lệnh cứu hộ qua mạng ngầm (SSH) và khởi động lại thành công!")
            return True
        else:
            raise Exception(result.stderr or result.stdout)
    except Exception as e:
        error_msg = f"❌ LỖI CỨU HỘ MÁY ARGO2: Không thể khởi động lại XAG training qua mạng ngầm. Lỗi: {e}"
        print(error_msg)
        send_tele_alert(error_msg)
        return False

def main():
    print(f"[{datetime.now().isoformat()}] Bắt đầu kiểm tra hệ thống định kỳ...")
    
    # 1. Check Local (Client1)
    if not check_local_running():
        restart_local()
    else:
        print("Local (Client1): OK")
        
    # 2. Check Remote (Argo2)
    if not check_argo2_running():
        restart_argo2()
    else:
        print("Remote (Argo2): OK")
        
    print("Kiểm tra hoàn tất.")

if __name__ == "__main__":
    main()
