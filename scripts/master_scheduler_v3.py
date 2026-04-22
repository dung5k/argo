import os
import sys
import time
import subprocess

CLIENT_ID = "client1"
CHECK_INTERVAL_SECONDS = 1200

# The sequence of training tasks to cycle through
TASKS = [
    {
        "session": "ny",
        "file": "workspaces/CFG_XAU_NY_V3_5"
    },
    {
        "session": "asian",
        "file": "workspaces/CFG_XAU_ASIAN_V3_5"
    },
    {
        "session": "london",
        "file": "workspaces/CFG_XAU_LONDON_V3_5"
    }
]

def check_client_status():
    """Runs host_controller.py status and returns True if client1 is IDLE."""
    cmd = [
        sys.executable,
        "src/orchestration/host_controller.py",
        "status",
        "--client-id",
        CLIENT_ID
    ]
    try:
        # We need a small timeout because status polls for ~5 seconds
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = res.stdout + res.stderr
        if "💤 IDLE" in output and CLIENT_ID in output:
            return True
        return False
    except Exception as e:
        print(f"Lỗi kiểm tra status: {e}")
        return False

def dispatch_training(task):
    """Triggers the train command for the specified task."""
    print(f"\n🚀 [SCHEDULER] Dispatching training for {task['session']} using config {task['file']}...")
    cmd = [
        sys.executable,
        "src/orchestration/host_controller.py",
        "train",
        "--client-id",
        CLIENT_ID,
        "--session",
        task["session"],
        "--file",
        task["file"],
        "--script",
        "src/training_v3/train_v3.py",
        "--mode",
        "MAX",
        "--time",
        "10" # Just listen for 10 seconds to confirm
    ]
    try:
        subprocess.run(cmd)
    except Exception as e:
        print(f"Lỗi gửi lệnh train: {e}")

def main():
    print("=========================================================================")
    print(f"🤖 KÍCH HOẠT MASTER SCHEDULER V3 (Quản đốc tự động cho {CLIENT_ID})")
    print(f"Chu kỳ quét: {CHECK_INTERVAL_SECONDS} giây")
    print("Danh sách nhiệm vụ:")
    for t in TASKS:
        print(f"  - {t['session'].upper()} -> {t['file']}")
    print("=========================================================================\n")

    task_idx = 0
    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Kiểm tra trạm {CLIENT_ID}...")
            is_idle = check_client_status()
            
            if is_idle:
                print(f"✅ {CLIENT_ID} đang rảnh! Lấy cấu hình tiếp theo: {TASKS[task_idx]['session']}")
                dispatch_training(TASKS[task_idx])
                
                # Tiến chỉ mục vòng lặp
                task_idx = (task_idx + 1) % len(TASKS)
                
                # Đợi một chút để client nhận lệnh chuyển sang BUSY trước khi check lại
                print("Đợi 30 giây để Client khởi động...")
                time.sleep(30)
            else:
                print(f"🔄 {CLIENT_ID} đang bận (BUSY/OFFLINE). Ngủ {CHECK_INTERVAL_SECONDS} giây...")
                
            time.sleep(CHECK_INTERVAL_SECONDS)
            
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user.")
            break

if __name__ == "__main__":
    main()
