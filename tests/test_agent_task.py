import os
import time
import json
from pathlib import Path

# Đường dẫn gốc
BASE_DIR = Path(r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor")

def get_client_id():
    client_id_file = BASE_DIR / ".client_id"
    if client_id_file.exists():
        return client_id_file.read_text(encoding="utf-8").strip()
    return "client1"  # Default fallback

def run_test():
    client_id = get_client_id()
    action_request_dir = BASE_DIR / client_id / "action_request"
    
    # Đảm bảo thư mục tồn tại
    action_request_dir.mkdir(parents=True, exist_ok=True)
    
    task_file = action_request_dir / "test_antigravity_task.json"
    
    # 1. Tạo Pending Task
    task_data = {
        "id": "test_antigravity_task",
        "type": "EXECUTE",
        "command": "python",
        "args": ["-c", "import time; print('Antigravity Unit Test is running!'); time.sleep(2)"],
        "cwd": ".",
        "status": "PENDING"
    }
    
    print(f"[*] Đang tạo Pending Task tại: {task_file}")
    with open(task_file, "w", encoding="utf-8") as f:
        json.dump(task_data, f, indent=4)
        
    print("[*] Task 'PENDING' đã được ném vào không gian của Agent. Bắt đầu chờ...")
    
    # 2. Vòng lặp chờ phản hồi từ Antigravity Agent (Client Master)
    timeout = 30 # Chờ tối đa 30 giây
    elapsed = 0
    poll_interval = 2
    
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        # Đọc lại nội dung file để xem JSON bị bên kia update thế nào
        if not task_file.exists():
            print(f"[-] Cảnh báo: File {task_file.name} đã biến mất!")
            continue
            
        try:
            with open(task_file, "r", encoding="utf-8") as f:
                current_data = json.load(f)
                
            status = current_data.get("status")
            print(f"[{elapsed}s] Tình trạng hiện tại: {status}")
            
            if status == "RUNNING":
                print("[+] Tuyệt vời! Antigravity (Client Master) ĐÃ NHÌN THẤY và ĐANG THỰC THI (RUNNING) task này.")
            elif status == "DONE":
                print("[+] Xong! Antigravity đã execute thành công (DONE).")
                print(f"    Exit Code: {current_data.get('exit_code')}")
                if "log_file" in current_data:
                    log_path = BASE_DIR / current_data["log_file"]
                    print(f"    Log lưu tại: {log_path}")
                break
            elif status == "FAILED":
                print("[-] Task đã thất bại (FAILED).")
                print(f"    Lỗi: {current_data.get('error')}")
                break
                
        except json.JSONDecodeError:
            print(f"[{elapsed}s] File đang bị ghi đè, đọc thử lại sau...")
            
    if elapsed >= timeout:
        print("[-] Hết thời gian chờ (Timeout). Antigravity Agent bên kia không phản hồi (có thể nó chưa được bật).")

if __name__ == "__main__":
    run_test()
