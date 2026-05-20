"""
Telegram Listener Watchdog
- Chay nen hoan toan doc lap voi AI (KHONG ton token)
- Cu 60 giay kiem tra 1 lan, neu listener chet thi tu dong khoi dong lai
"""
import os
import sys
import time
import subprocess

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LISTENER_SCRIPT = os.path.join(SCRIPT_DIR, 'telegram_listener.py')
CHECK_INTERVAL = 60  # giây

listener_proc = None

def is_listener_alive():
    global listener_proc
    if listener_proc is None:
        return False
    return listener_proc.poll() is None  # None = đang chạy

def start_listener():
    global listener_proc
    print(f"[WATCHDOG] Khởi động telegram_listener.py...", flush=True)
    listener_proc = subprocess.Popen(
        [sys.executable, LISTENER_SCRIPT],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace'
    )
    print(f"[WATCHDOG] Listener đã start, PID={listener_proc.pid}", flush=True)

def main():
    print("[WATCHDOG] Bắt đầu giám sát Telegram Listener (0 token, 100% tự động)...", flush=True)
    
    # Khởi động listener lần đầu
    start_listener()

    while True:
        time.sleep(CHECK_INTERVAL)
        
        if not is_listener_alive():
            # Listener đã tắt (do có tin nhắn mới -> AI xử lý)
            # Chờ thêm 5 giây để AI có thể đã tự khởi động lại
            time.sleep(5)
            if not is_listener_alive():
                print(f"[WATCHDOG] Listener không còn chạy! Tự động khởi động lại...", flush=True)
                start_listener()
            else:
                print(f"[WATCHDOG] Listener đã được AI restart rồi, OK.", flush=True)
        else:
            print(f"[WATCHDOG] Listener đang chạy bình thường (PID={listener_proc.pid})", flush=True)

if __name__ == "__main__":
    main()
