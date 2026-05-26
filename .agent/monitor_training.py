import os
import glob
import json
import random
from datetime import datetime
import time
import psutil

def find_latest_log(base_dir):
    search_pattern = os.path.join(base_dir, "workspaces", "CFG_LTC_*", "runs", "*", "train_v6.log")
    logs = glob.glob(search_pattern)
    if not logs:
        return None
    latest_log = max(logs, key=os.path.getmtime)
    return latest_log

def main():
    base_dir = r"d:\DungLA\client1"
    tasks_file = os.path.join(base_dir, ".agent", "tasks.json")
    
    latest_log = find_latest_log(base_dir)
    if not latest_log:
        message = "⚠️ Hệ thống Giám Sát: Không tìm thấy bất kỳ file log đào tạo nào!"
    else:
        mtime = os.path.getmtime(latest_log)
        time_diff = time.time() - mtime
        
        # Kiểm tra process train_v6.py
        is_running = False
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if proc.info['name'] in ['python.exe', 'python'] and any('train_v6.py' in cmd for cmd in cmdline):
                    is_running = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not is_running:
            message = "🚨 CẢNH BÁO CRITICAL: Tiến trình train_v6.py ĐÃ CHẾT hoàn toàn! (Không tìm thấy trong Process List)"
        elif time_diff > 1800: # 30 minutes
            message = f"🚨 CẢNH BÁO TREO APP: Tiến trình train_v6.py đang chạy nhưng BỊ TREO (không có log mới trong {int(time_diff/60)} phút)!\nLog cuối tại: {latest_log.split('workspaces')[-1]}"
        else:
            # Read the last few lines to find progress
            with open(latest_log, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            progress = "Đang khởi tạo hoặc chưa có thông tin Epoch."
            for line in reversed(lines):
                if line.startswith("[Epoch") or line.startswith("[Warm-up]"):
                    progress = line.strip()
                    break
            
            session_name = latest_log.split("CFG_LTC_")[1].split("_V6")[0]
            message = f"🟢 TRẠNG THÁI ĐÀO TẠO (Phiên {session_name}): Đang chạy tốt!\n\nTiến độ mới nhất:\n`{progress}`"

    # Append to tasks.json
    try:
        with open(tasks_file, "r", encoding="utf-8") as f:
            tasks = json.load(f)
    except:
        tasks = []
        
    tasks.append({
        "task_id": random.randint(1000000, 9999999),
        "status": "completed",
        "prompt": "system_auto_monitor",
        "chat_id": 1816854047,
        "reply_message": message,
        "reply_status": "pending",
        "timestamp": datetime.now().isoformat()
    })
    
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
        
if __name__ == "__main__":
    main()
