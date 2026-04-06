---
description: Cách tương tác với Client (Distributed AI Nodes) thông qua MQTT
---

# Quy trình tương tác với Client qua MQTT

Trong kiến trúc phân tán ARGO AI, các trạm huấn luyện (Client1, Client2...) được đặt ở các máy tính vật lý khác nhau hoặc hoạt động trong môi trường độc lập.
Dưới đây là các KHUYẾN NGHỊ và CẤM KỴ khi tương tác với Client để đảm bảo an toàn phân tán.

## 🚫 Điều Cấm Kỵ (KHÔNG ĐƯỢC LÀM)
1. **Tuyệt đối KHÔNG `cd`** vào các thư mục `client1`, `client2` nằm trên OneDrive hoặc mổ trực tiếp vào cấu trúc của chúng để sửa file. Các file này thuộc quyền kiểm soát của máy trạm từ xa!
2. Không cho rằng một lệnh `git push` ở Host sẽ lập tức tự động cập nhật được lên Client, vì quá trình đồng bộ Git có thể bị khóa hoặc kẹt bởi hệ điều hành máy trạm.

## ✅ Quy Trình Chuẩn Điểu Khiển Qua MQTT
Mọi tương tác từ xa phải thông qua Trạm Kiểm Soát Trung Tâm `host_controller.py` được vận hành và điều tiết bằng giao thức MQTT.

### 1. Gửi File Trực Tiếp Sang Client (`send_file`)
Khi sửa đổi file Training hoặc bot config và muốn Client NHẬN ĐƯỢC NGAY LẬP TỨC mà không cần thông qua Git pull, hãy dùng lệnh `send_file`. Tính năng này sẽ nén Base64 và đẩy thẳng vào ổ cứng Client!
```powershell
# Gửi tệp train_unified.py từ ổ Host đè thẳng lên ổ Client1
python src\orchestration\host_controller.py send_file -c client1 --file "src/core/train_unified.py" --dest "src/core/train_unified.py"
```

### 2. Gửi Lệnh Thực Thi Code Độc Lập (`run_code`)
Để ép Client thực thi một đoạn mã Python, thao tác dọn dẹp hệ thống hoặc Fix Git, hãy tận dụng cờ `--raw` của tính năng `run`:
```powershell
# Ví dụ: Ép Client1 tự dọn dẹp Git nội bộ
python src\orchestration\host_controller.py run -c client1 --raw --script "import subprocess; subprocess.run(['git', 'fetch', '--all']); subprocess.run(['git', 'reset', '--hard', 'origin/main'])"
```

### 3. Tái Khởi Động Tiến Trình Train
Mọi thay đổi Code/File trên Client sẽ CHƯA CÓ HIỆU LỰC nếu tiến trình Train cũ đang treo trên RAM. Cần tiến hành Combo Stop/Start:
```powershell
# Bắn tín hiệu tiêu diệt tiến trình cũ đang nghẽn
python src\orchestration\host_controller.py kill -c client1

# Chờ 3-5 giây rồi kích hoạt lại tiến trình Train mới (lựa chọn mã symbol tuỳ cấu hình)
python src\orchestration\host_controller.py train -c client1 -s xauusd -t 15
```

### 4. Tổng Kết Khi Cập Nhật Hệ Thống
Bất cứ khi nào cập nhật luồng lõi (`train_unified.py`), hãy thực hiện combo chuẩn:
1. `git add/commit/push` ở Host.
2. `send_file` đè trực tiếp qua MQTT để đẩy nhanh file mà không lo nghẽn mạng!
3. `kill` và `train` để khởi động nhịp mới ở Client.

### 5. Nâng cấp bản thân Agent (`deploy_agent`)
Đôi khi bạn cần thay đổi logic của chính file chạy nền `client_tg_agent.py` trên các máy trạm (ví dụ thêm lệnh MQTT mới). Do Agent đang chạy vòng lặp vô tận, bạn không thể xóa đè nó bình thường. Hệ thống ARGO có tính năng Deploy riêng:
```powershell
# B1: Đóng gói và lưu phiên bản Agent hiện tại (tại Host)
python src\orchestration\host_controller.py save_version -v "v2.0"

# B2: "Bắn" khối mã Agent V2.0 sang toàn bộ các Client.
# Các Client sẽ nhận tín hiệu, tải bản cập nhật, tự động ghi đè và Restart lại toàn bộ vòng lặp Agent của chính nó!
python src\orchestration\host_controller.py deploy_agent -v "latest"
```
