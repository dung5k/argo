---
description: Auto Git Commit and Push Rule
---

# Git Commit Policy

**MANDATORY RULE FOR AI AGENT:**
Sau khi thực hiện bất kỳ thay đổi nào (Code Edits) trên mã nguồn của dự án này, Agent **BẮT BUỘC** phải tự động gọi lệnh Terminal để Git Commit và Git Push (nếu môi trường cho phép) thay đổi đó trước khi báo cáo kết quả lại cho User.

**Workflow Action:**
1. Call `git add <file(s)>`
2. Call `git commit -m "bot: <mô tả ngắn gọn tiếng Việt>"`
3. Call `git push` (optional: continue if it fails due to branching)

*Mục đích: Đảm bảo mọi thay đổi trên môi trường Live/Production của User luôn được lưu vết lên Source Control (Github/Gitlab).*
