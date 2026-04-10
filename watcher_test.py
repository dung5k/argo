import os
import time
import shutil

base_dir = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\.agent"
pending_dir = os.path.join(base_dir, "pending")
processed_dir = os.path.join(base_dir, "processed")

# Đảm bảo đã có đủ thư mục
os.makedirs(pending_dir, exist_ok=True)
os.makedirs(processed_dir, exist_ok=True)

print(f"👀 Đang theo dõi thư mục {os.path.basename(pending_dir)}... (Nhấn Ctrl+C để thoát)")

while True:
    try:
        # Bắt đầu vòng lặp quét file mỗi 2 giây
        for f in os.listdir(pending_dir):
            if f.endswith(".json"):
                file_path = os.path.join(pending_dir, f)
                print(f"\n🔥 [BÁO ĐỘNG] Phát hiện file mới: {f}")
                print("Đang đọc nội dung file:")
                
                with open(file_path, "r", encoding="utf-8") as json_file:
                    print(json_file.read())
                    
                print("\n⏳ Giả lập Antigravity đang xử lý...")
                time.sleep(2) # Giả lập thời gian AI chạy mất 2 giây
                
                # Xử lý xong thì dọn dẹp file sang processed
                target_path = os.path.join(processed_dir, f)
                
                # xoá file trùng tên trong target nếu có
                if os.path.exists(target_path):
                    os.remove(target_path)
                    
                shutil.move(file_path, target_path)
                print(f"✅ Đã xử lý xong và dọn dẹp file sang mục processed!")
                print("-----------------------------------")
    except Exception as e:
        pass
    
    time.sleep(2)
