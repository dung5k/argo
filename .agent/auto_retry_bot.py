import time
import os
try:
    import pyautogui
except ImportError:
    print("Đang cài đặt pyautogui và opencv-python...")
    os.system("pip install pyautogui opencv-python")
    import pyautogui

print("="*50)
print("🤖 AUTO RETRY BOT CHO ANTIGRAVITY")
print("="*50)
print("Hướng dẫn:")
print("1. Dùng Snipping Tool (Win + Shift + S) chụp lại chính xác cái nút 'Retry' hoặc 'Thử lại' trên giao diện.")
print("2. Lưu hình ảnh đó vào cùng thư mục với script này, đặt tên là 'retry_btn.png'.")
print("3. Để nguyên màn hình IDE mở để script quét và tự động bấm.")
print("Đang chạy ngầm... (Bấm Ctrl+C để thoát)")

button_image = "retry_btn.png"

if not os.path.exists(button_image):
    print(f"\n[CẢNH BÁO] Chưa tìm thấy file '{button_image}'!")
    print("Vui lòng chụp nút Retry và lưu lại với tên 'retry_btn.png' rồi chạy lại script.")
else:
    print("\n[OK] Đã tìm thấy mẫu nút. Bắt đầu quét màn hình mỗi 5 giây...")
    while True:
        try:
            # Tham số confidence=0.8 yêu cầu cài opencv-python để tìm kiếm mờ (phòng khi màu sắc hơi lệch)
            location = pyautogui.locateOnScreen(button_image, confidence=0.8)
            if location:
                center = pyautogui.center(location)
                print(f"[{time.strftime('%H:%M:%S')}] Phát hiện nút Retry! Đang tự động click...")
                pyautogui.click(center)
                # Đợi 1 lúc sau khi click để tránh click đúp
                time.sleep(5)
        except Exception as e:
            # Lỗi thường là do không tìm thấy hình trên màn hình, cứ bỏ qua
            pass
        
        time.sleep(5)
