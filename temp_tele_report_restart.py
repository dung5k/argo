# -*- coding: utf-8 -*-
import subprocess

msg = """✅ [BOT RESTART] Sếp Lê, tôi đã khởi động lại thành công cả 2 bot Live Trade!

🔄 TIẾN TRÌNH:
1. Đã dọn dẹp các tiến trình bot cũ đang chạy.
2. Đã gọi `start_bots.py` khởi động song song 2 Bot dưới nền:
   - **LTC V6 MTF**: Đã load cấu hình siêu lợi nhuận (Vòng 68 - HolyGrail_34).
   - **XAG V3.5**: Đã nạp lại trạng thái.

Hệ thống Live Trade đang trực chiến với vũ khí mạnh nhất! 🚀"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
