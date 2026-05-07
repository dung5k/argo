import requests
import json

def send_report():
    token = "8057292338:AAF2EnD_V9dWVNiDPnEfPEyYMKHxJQnNzlg"
    chat_id = "1816854047"
    
    report = """<b>🔴 BÁO CÁO GIÁM SÁT HỆ THỐNG PROD (HÀNG GIỜ)</b>
📅 Thời gian: 03/05/2026 22:40

⚠️ <b>CÁC LỖI NGHIÊM TRỌNG PHÁT HIỆN:</b>

1. ❌ <b>Lỗi Logic Google Sheets:</b>
   - Nội dung: <code>Missing required parameters: spreadsheetId</code>
   - Tần suất: Rất cao (flooding logs)
   - Đề xuất: Kiểm tra cấu hình biến môi trường hoặc tham số truyền vào hàm lấy danh sách nhân viên.

2. ❌ <b>Lỗi Crash ChatTestController:</b>
   - Nội dung: <code>TypeError: Cannot destructure property 'bot_id' of 'req.body' as it is undefined</code>
   - Vị trí: <code>ChatTestController.handleChatMessage</code>
   - Đề xuất: Thêm kiểm tra điều kiện (validation) cho req.body trước khi destructure để tránh crash.

3. ⚠️ <b>Lỗi Cache Manager:</b>
   - Nội dung: <code>Cần cung cấp clientConfig có PAGE_ID để rebuild cache.</code>
   - Đề xuất: Kiểm tra lại logic khởi tạo CacheManager.

🔒 <b>Bảo mật:</b> Phát hiện nhiều nỗ lực scan (bot) truy cập /.git/config và wp-admin. Hệ thống đã chặn thành công (AUTH_FAIL).

✅ <b>Trạng thái Database:</b> Không phát hiện lỗi kết nối.
✅ <b>Trạng thái AI Model:</b> Không phát hiện lỗi OpenRouter.
"""
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": report,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=20)
        if response.status_code == 200:
            print("Telegram message sent successfully.")
        else:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram: {e}")

if __name__ == "__main__":
    send_report()
