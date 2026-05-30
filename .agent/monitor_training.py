import os
import glob
import json
import random
from datetime import datetime
import subprocess

def main():
    base_dir = r"d:\DungLA\client1"
    tasks_file = os.path.join(base_dir, ".agent", "tasks.json")
    
    try:
        # Run check script on ARGO2 via SSH
        result = subprocess.check_output(
            ['ssh', 'dungla@192.168.1.18', 'C:\\argo\\venv\\Scripts\\python.exe D:\\DungLA\\Argo\\check_argo2_training.py'],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        
        if result == "NO_LOG":
            message = "⚠️ Hệ thống Giám Sát (ARGO2 - XAG): Không tìm thấy bất kỳ file log đào tạo nào!"
        elif result == "NOT_RUNNING":
            message = "🚨 CẢNH BÁO CRITICAL (ARGO2 - XAG): Tiến trình train_v6.py ĐÃ CHẾT hoàn toàn! (Không tìm thấy trong Process List)"
        elif result.startswith("HANG|"):
            log_path = result.split("|", 1)[1]
            message = f"🚨 CẢNH BÁO TREO APP (ARGO2 - XAG): Tiến trình train_v6.py đang chạy nhưng BỊ TREO (không có log mới trong 30 phút)!\nLog cuối tại: {log_path.split('workspaces')[-1]}"
        elif result.startswith("OK|"):
            parts = result.split("|", 2)
            session_name = parts[1]
            progress = parts[2]
            message = f"🟢 TRẠNG THÁI ĐÀO TẠO (ARGO2 - XAG - Phiên {session_name}): Đang chạy tốt!\n\nTiến độ mới nhất:\n`{progress}`"
        else:
            message = f"⚠️ Hệ thống Giám Sát (ARGO2 - XAG): Dữ liệu trả về không hợp lệ: {result}"
            
    except subprocess.CalledProcessError as e:
        message = f"⚠️ Lỗi kết nối SSH đến ARGO2: {e.output}"
    except Exception as e:
        message = f"⚠️ Lỗi hệ thống giám sát: {str(e)}"

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
