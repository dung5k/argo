# Telegram Bridge & Auto-Clicker Tool

Tool này được sử dụng để tạo một cầu nối (Bridge) giữa một Bot Telegram và một hệ thống/IDE cục bộ. Nó cho phép bạn gửi tin nhắn/câu lệnh từ Telegram, công cụ sẽ ghi nhận lại vào một file `tasks.json` để IDE đọc, và đồng thời nó cũng cho phép cấu hình một luồng Auto-Clicker hoạt động ngầm (dựa vào nhận diện hình ảnh).

## Cấu trúc

- `main.py`: File khởi chạy chính. Lắng nghe Telegram bot, đọc/ghi file `tasks.json` để giao tiếp với IDE. Khởi chạy luồng Auto Clicker.
- `auto_clicker.py`: Chứa logic chụp ảnh màn hình và so sánh với ảnh mẫu (template matching) để tự động click chuột.
- `config.json`: File cấu hình dùng chung cho toàn bộ tool.
- `templates/`: Thư mục chứa các ảnh mẫu (`.png`) mà bạn muốn Auto Clicker tìm kiếm trên màn hình.
- `run_bridge.bat`: File kịch bản chạy nhanh trên Windows.

## Hướng dẫn thiết lập

### 1. Chuẩn bị Python
Yêu cầu cài đặt các thư viện:
```bash
pip install opencv-python numpy mss pyautogui urllib3
```

### 2. Cấu hình Bot Telegram
Mở file `config.json` và chỉnh sửa các trường sau:
- `bot_token`: Lấy từ BotFather trên Telegram khi bạn tạo bot mới.
- `allowed_chat_ids`: Danh sách các ID của những người dùng được phép nhắn tin cho bot.
- `tasks_file`: Đường dẫn tới file `tasks.json` nơi IDE sẽ đọc lệnh. Có thể dùng đường dẫn tương đối (ví dụ `../.agent/tasks.json`) hoặc đường dẫn tuyệt đối.

### 3. Cấu hình Auto-Clicker
Trong `config.json`, phần `auto_clicker`:
- `enabled`: `true` hoặc `false` để bật/tắt Auto Clicker.
- `scan_interval`: Thời gian quét lại màn hình (giây) nếu không tìm thấy mẫu.
- `cooldown_after_click`: Thời gian nghỉ ngơi (giây) sau khi click thành công 1 lần.
- `confidence_threshold`: Độ chính xác yêu cầu (0.0 đến 1.0). Nên để 0.85 -> 0.9 để tránh click nhầm.
- `region`: Vùng chụp màn hình để tìm kiếm. Giúp giảm tải CPU thay vì chụp toàn màn hình.

### 4. Thiết lập ảnh mẫu (Templates)
Cắt/chụp ảnh các nút bấm hoặc khu vực bạn muốn tự động click (như nút "Claim", "Confirm", v.v.) và lưu dưới định dạng `.png`. Đặt tất cả các file ảnh này vào thư mục `templates/`.
Công cụ sẽ liên tục quét thư mục này, vì vậy bạn có thể ném file mới vào bất kỳ lúc nào mà không cần khởi động lại.

## Cách chạy
Chỉ cần click đúp vào file `run_bridge.bat` hoặc chạy lệnh:
```bash
python main.py
```
