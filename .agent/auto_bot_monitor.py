import os
import sys
import glob
import time
import subprocess
import psutil
from datetime import datetime, timezone
import json
import io
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BOT_DIR = r"d:\DungLA\client1"
LOG_DIR = os.path.join(BOT_DIR, "workspaces", "shared_meta", "logs")
LTC_BAT = os.path.join(BOT_DIR, "run_bot_v6_ltc.bat")
XAG_BAT = os.path.join(BOT_DIR, "run_bot_xag.bat")
LTC_SCHED = os.path.join(BOT_DIR, "bot_schedule_v6_ltc.json")
XAG_SCHED = os.path.join(BOT_DIR, "bot_schedule_xag.json")

def get_expected_run_id(schedule_path):
    if not os.path.exists(schedule_path): return None
    try:
        with open(schedule_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        sched = data.get("schedule", data.get("SCHEDULE", {}))
        now_utc = datetime.now(timezone.utc)
        hm = now_utc.strftime("%H:%M")
        for sess_name, sinfo in sched.items():
            start = sinfo.get("start", "00:00")
            end = sinfo.get("end", "23:59")
            if start <= end:
                if start <= hm <= end: return sinfo.get("run_id")
            else:
                if hm >= start or hm <= end: return sinfo.get("run_id")
    except Exception as e:
        print(f"Lỗi đọc schedule {os.path.basename(schedule_path)}: {e}")
    return None

def check_ghost_processes():
    bot_procs = []
    for p in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if p.info['name'] == 'python.exe' and p.info['cmdline']:
                cmd = " ".join(p.info['cmdline']).lower()
                if 'bot_v6.py' in cmd or 'bot_v3.py' in cmd:
                    bot_procs.append(p)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return bot_procs

def restart_bots():
    print(f"[{datetime.now()}] [RESTART] Khởi động lại Bot LTC và XAG...")
    procs = check_ghost_processes()
    for p in procs:
        try:
            print(f"  -> Đóng tiến trình {p.pid}...")
            p.kill()
        except Exception:
            pass
            
    time.sleep(2)
    try:
        subprocess.Popen(f'cmd /c start "" "{LTC_BAT}"', cwd=BOT_DIR, shell=True)
        time.sleep(1)
        subprocess.Popen(f'cmd /c start "" "{XAG_BAT}"', cwd=BOT_DIR, shell=True)
        print(f"[{datetime.now()}] [OK] Đã gửi lệnh khởi động lại 2 bot.")
    except Exception as e:
        print(f"[{datetime.now()}] [ERROR] Lỗi khi khởi động lại bot: {e}")

def check_bot_health(minutes_back=30):
    log_files = glob.glob(os.path.join(LOG_DIR, "trade_bot_v6_*.log"))
    if not log_files:
        return "Không tìm thấy file log"
        
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"[{datetime.now()}] Phân tích log: {latest_log}")
    
    try:
        with open(latest_log, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        return f"Lỗi đọc log: {e}"

    lines = lines[-5000:]
    now = datetime.now()
    time_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    
    procs = check_ghost_processes()
    bot_start_time = None
    if procs:
        try:
            bot_start_time = max(p.create_time() for p in procs)
        except Exception:
            pass
    
    # 1. Kiểm tra Lỗi Exception
    error_keywords = [
        "Traceback (most recent call last):", 
        "[WinError 1455]", 
        "Lỗi suy diễn Pytorch", 
        "TỪ CHỐI SUY LUẬN", 
        "FATAL",
        "Lỗi Feature Engineering",
        "LỖI ÁNH XẠ DỮ LIỆU",
        "Lỗi Áp dụng Scaler"
    ]
    for line in reversed(lines):
        match = time_pattern.search(line)
        if match:
            try:
                log_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                if (now - log_time).total_seconds() > minutes_back * 60:
                    break
                if bot_start_time and log_time.timestamp() < bot_start_time:
                    continue # Bỏ qua các lỗi xảy ra TRƯỚC khi bot hiện tại bắt đầu chạy
            except ValueError:
                pass
        for kw in error_keywords:
            if kw in line:
                return f"Phát hiện lỗi nguy hiểm gần đây: {line.strip()}"
                
    # 2. Kiểm tra bộ não có khớp phiên không
    expected_ltc = get_expected_run_id(LTC_SCHED)
    expected_xag = get_expected_run_id(XAG_SCHED)
    
    actual_ltc = None
    actual_xag = None
    
    # Quét từ dưới lên để tìm lần tải não cuối cùng
    for line in reversed(lines):
        if "sync_explicit_model | run=" in line:
            # Ví dụ: 2026-05-05 08:29:21,011 [CloudManagerV3] ☁ Bắt đầu sync_explicit_model | run=run_20260424_040000_v3_asian_18 | cfg=CFG_LTC_ASIAN_V3_5
            match = re.search(r"run=([\w_-]+)\s*\|\s*cfg=([\w_-]+)", line)
            if match:
                run_val = match.group(1)
                cfg_val = match.group(2)
                if "LTC" in cfg_val and not actual_ltc:
                    actual_ltc = run_val
                if "XAG" in cfg_val and not actual_xag:
                    actual_xag = run_val
        if actual_ltc and actual_xag:
            break
            
    if expected_ltc and actual_ltc and actual_ltc != expected_ltc:
        return f"Sai não LTC: Kỳ vọng {expected_ltc}, Đang chạy {actual_ltc}"
    if expected_xag and actual_xag and actual_xag != expected_xag:
        return f"Sai não XAG: Kỳ vọng {expected_xag}, Đang chạy {actual_xag}"

    # 3. Kiểm tra Output (Có ra được quyết định không?)
    # Đếm số lượng dự đoán trong 4 phút qua
    recent_predictions = 0
    for line in reversed(lines):
        match = time_pattern.search(line)
        if match:
            try:
                log_time = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
                if (now - log_time).total_seconds() > 4 * 60:
                    break
                if "ĐÃ KẾT THÚC PIPELINE DỰ ĐOÁN" in line:
                    recent_predictions += 1
            except ValueError:
                pass
                
    # Nếu có bot nào vừa khởi động (dưới 5 phút) thì bỏ qua check output
    procs = check_ghost_processes()
    just_started = False
    for p in procs:
        try:
            if time.time() - p.create_time() < 300:
                just_started = True
                break
        except Exception:
            pass
            
    if not just_started and recent_predictions < 4:
        # Nếu chỉ có 2 bot, mỗi bot 1 nến/phút -> 4 phút phải có 8 nến. 
        # Để ngưỡng 4 là hơi thấp nhưng an toàn. 
        # Tuy nhiên nếu user báo không có output, ta nên kiểm tra kỹ hơn.
        return f"Kẹt Pipeline: Chỉ có {recent_predictions} tín hiệu trong 4 phút qua (Dự kiến >= 4). Có bot đang 'câm nín'!"

    return None

def main():
    print("="*50)
    print(f"[START] AUTO BOT MONITOR - Khởi chạy lúc {datetime.now()}")
    print("="*50)
    
    bot_procs = check_ghost_processes()
    if len(bot_procs) < 2:
        reason = f"Thiếu bot (hiện có {len(bot_procs)}/2 bot đang chạy)"
        print(f"[{datetime.now()}] [ALERT] {reason}. Tiến hành Fix & Restart...")
        restart_bots()
        return

    error_reason = check_bot_health(minutes_back=30)
    
    if error_reason:
        print(f"[{datetime.now()}] [ALERT] {error_reason}. Tiến hành Fix & Restart...")
        restart_bots()
    else:
        print(f"[{datetime.now()}] [OK] Hệ thống Bot đang hoạt động bình thường, xuất tín hiệu đều đặn và nạp đúng NÃO. Không cần can thiệp.")
        
if __name__ == "__main__":
    main()
