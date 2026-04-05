import os
import sys
import glob

def print_log():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(base_dir, "clientGH", "logs")
    
    if not os.path.exists(logs_dir):
        print("Không có thư mục log.")
        return
        
    log_files = glob.glob(os.path.join(logs_dir, "*_train.log"))
    if not log_files:
        print("Trống (Chưa có log training).")
        return
        
    latest_log = max(log_files, key=os.path.getmtime)
    print(f"📄 Đang đọc file: {os.path.basename(latest_log)}")
    print("="*50)
    
    with open(latest_log, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        
    important_lines = [l.strip() for l in lines if any(kw in l for kw in ["Epoch", " WR", "VLoss", "ĐỈNH", "PHOENIX", "TRANSFER"])]
    if not important_lines:
        print("Đang huấn luyện, chưa xong Epoch 1...")
        print("\n".join(lines[-5:]))
    else:
        print("\n".join(important_lines[-15:]))
        
if __name__ == "__main__":
    print_log()
