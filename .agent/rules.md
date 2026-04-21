---
description: Auto Git Commit and Push Rule
---

# Git Commit Policy

**MANDATORY RULE FOR AI AGENT:**
Sau khi thực hiện bất kỳ thay đổi nào (Code Edits) trên mã nguồn của dự án này, Agent **BẮT BUỘC** phải tự động gọi lệnh Terminal để Git Commit và Git Push (nếu môi trường cho phép) thay đổi đó trước khi báo cáo kết quả lại cho User.

**Workflow Action:**
1. Call `git add <file(s)>`
2. Call `git commit -m "bot: <mô tả ngắn gọn tiếng Việt>"`
3. Call `git pull --no-edit` (BẮT BUỘC: Pull code về và tự động merge nếu có xung đột nhẹ để đồng bộ với Remote)
4. Call `git push` (BÁO CÁO: nếu push hoặc pull thất bại do merge conflict phức tạp, cần báo người dùng can thiệp)


# Nguyên tắc code
- Việc code luôn luôn cần tách thành class và hàm có tính năng và nhiệm vụ động lập, có input và output đơn giản

- Sau khi code hoàn thành 1 hàm thì cần viết unit test để đảm bảo hàm đấy chạy đúng

- Hạn chế hardcode, cần viết code cho bài toán tổng quát, các giá trị hardcode cần được đưa vào file config

# Thực thi nhiệm vụ tạm thời (Temporary Tasks)
- Mỗi khi thực hiện một nhiệm vụ TẠM THỜI mà yêu cầu sinh/tạo ra file code (để test thử, kiểm tra, cào dữ liệu nháp...), BẮT BUỘC phải tạo file đó trong thư mục `temp/`.
- Sau khi chạy và có kết quả xong, BẮT BUỘC phải tự động XÓA file tạm đó đi để dọn dẹp sạch sẽ không gian làm việc.


# Quản lý Tiến trình (Process Management)
- Tắt ứng dụng / bot một cách AN TOÀN (Safe Stop).
- NGHIÊM CẤM sử dụng biện pháp kill tiến trình python một cách thô bạo (vd: Get-Process python | Stop-Process) vì máy tính còn chạy nhiều ứng dụng python khác.
- Để tắt một bot, cần tìm chính xác process thông qua CommandLine (vd: wmic process where "name='python.exe' and commandline like '%tên_script.py%'" call terminate).
