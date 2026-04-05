---
description: Bắt buộc Git Commit sau mỗi lần sửa code
---

# Lệnh Bài: Bắt Buộc Git Commit Liên Tục

Bất cứ khi nào tôi (Antigravity hoặc các AI Agent khác) thực hiện sửa đổi mã nguồn (`replace_file_content`, `multi_replace_file_content`, `write_to_file`...) hoặc tạo một thư mục mới có tính logic cao, hệ thống yêu cầu bảo toàn trạng thái bằng cách:

- [ ] 1. Gọi lệnh `git add .` thông qua môi trường Command.
- [ ] 2. Gọi lệnh `git commit -m "[Loại thao tác]: [Mô tả ngắn gọn code vừa sửa]"` thông qua môi trường Command.

**Tuyệt đối không được chuyển sang việc khác nếu chưa thực hiện thao tác Commit này**, để USER luôn có một điểm neo khôi phục (checkpoint) đề phòng AI có sinh ra mã nguồn sai ở bước tiếp theo.
