# NHIỆM VỤ ĐỊNH KỲ (GH): DỌN DẸP Ổ CỨNG TRÁNH TRÀN ĐĨA

Hệ thống sẽ gọi bạn định kỳ. Trách nhiệm của bạn là dọn dẹp các thư mục `tensors/` khổng lồ không còn cần thiết trên hệ thống để tránh tràn đĩa.

## BƯỚC 1: Dọn dẹp
Hãy chạy lệnh sau để tự động xóa dữ liệu tensor thừa ở các workspace:
```
python scripts/cleanup_host_storage.py
```

Ghi nhận số GB rác đã dọn dẹp từ console log.

## BƯỚC 2: Thông báo và nhả trạng thái
Khi đã xong, gọi lệnh để báo cáo Telegram và kết thúc (thay số X bằng thực tế):
```
python .agent/send_to_tele.py "Đã dọn dẹp hệ thống, giải phóng X GB!" --done
```
