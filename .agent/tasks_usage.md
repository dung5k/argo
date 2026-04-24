# Hướng dẫn sử dụng file cấu hình lịch trình `tasks.json`

Hệ thống Extension hiện tại sử dụng file `tasks.json` để quản lý nhiều tác vụ định kỳ độc lập. Cấu trúc file này cho phép **AI tự thiết lập thời gian chạy tiếp theo** nếu cần thiết.

## 1. Cấu trúc cơ bản
Mở file `.agent/tasks.json`, bạn sẽ thấy danh sách các tác vụ:
```json
{
  "tasks": [
    {
      "id": "xag_ny_auto_tuning",
      "enabled": true,
      "promptFile": ".agent/periodic_prompt_xag_ny.md",
      "nextRunTime": 1714000000000,
      "intervalMinutes": 10
    }
  ]
}
```

## 2. Giải thích các trường:
- `id`: Định danh duy nhất cho task.
- `enabled`: Chuyển sang `false` nếu muốn tắt tác vụ này hoàn toàn.
- `promptFile`: Đường dẫn đến file `.md` chứa chỉ thị/nhiệm vụ gửi cho AI khi task kích hoạt.
- `nextRunTime`: Timestamp (tính bằng mili-giây) chỉ định thời điểm *sớm nhất* mà task sẽ được kích hoạt. **Nếu giá trị là 0, nó sẽ chạy ngay lập tức.**
- `intervalMinutes`: Sau khi task được kích hoạt (gửi cho AI), Extension sẽ tự động cộng thêm khoảng thời gian này vào `nextRunTime` để chuẩn bị cho chu kỳ tiếp theo.

## 3. Cách AI thay đổi thời gian chạy ở lượt tiếp theo
Trong quá trình xử lý tác vụ, nếu AI thấy rằng không cần phải chạy lại sau `intervalMinutes` mặc định (ví dụ mặc định là 10 phút, nhưng AI muốn chạy lại sau 5 phút hoặc 2 tiếng nữa), AI có thể sử dụng công cụ Python (hoặc sửa file trực tiếp) để cập nhật giá trị `nextRunTime` của chính task đó trong `tasks.json`.
Ví dụ logic của Python:
```python
import json, time
with open('.agent/tasks.json', 'r') as f:
    data = json.load(f)
for task in data['tasks']:
    if task['id'] == 'xag_ny_auto_tuning':
        # Đặt lịch chạy lại sau đúng 5 phút kể từ hiện tại
        task['nextRunTime'] = int((time.time() + 5 * 60) * 1000)
with open('.agent/tasks.json', 'w') as f:
    json.dump(data, f, indent=2)
```

⚠️ **Lưu ý quan trọng**: Khi file `tasks.json` được AI sửa, Extension sẽ đọc lại nó. Nếu AI vừa tự set lịch mới, AI cần kết thúc quy trình bình thường bằng cách gọi `send_to_tele.py "--done"` để nhả trạng thái rảnh cho Extension.
