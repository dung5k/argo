---
trigger: always_on
---

- Việc code luôn luôn cần tách thành class và hàm có tính năng và nhiệm vụ động lập, có input và output đơn giản

- Sau khi code hoàn thành 1 hàm thì cần viết unit test để đảm bảo hàm đấy chạy đúng

- Hạn chế hardcode, cần viết code cho bài toán tổng quát

- Mỗi khi cập nhật/thêm tính năng mới vào luồng đào tạo (như train_unified.py), BẮT BUỘC đặt biến `RUN_VERSION_DESC` ở đầu file. Đảm bảo in dòng log `[VERSION_INFO] ...` ở ĐÚNG VỊ TRÍ, cụ thể là SAU KHI ống log ghi đĩa đã được mở (sau lệnh `sys.stdout = TeeLogger(...)`) để đảm bảo hệ thống chặn log Telegram bắt được thông điệp này.