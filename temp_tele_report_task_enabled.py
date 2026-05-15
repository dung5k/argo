# -*- coding: utf-8 -*-
import subprocess

msg = """✅ [TASK SCHEDULER] Sếp Lê, tôi đã thiết lập xong Task kiểm tra định kỳ cho Phiên London!

⚙️ CẤU HÌNH TASK SCHEDULER (.agent/tasks.json):
- Task ID: `ltc_london_v6_auto_tuning`
- Trạng thái: ✅ ENABLED (đã bật)
- Chu kỳ: Mỗi 30 phút tự động kích hoạt 1 lần
- Trigger: `ltc_london_v6_training_done` (kích hoạt khi Training hoàn tất)
- Lần chạy tiếp theo: ~5 phút nữa (08:11 giờ HN)

🔴 Task Phiên Á (`ltc_asian_v6_auto_tuning`): Giữ nguyên DISABLED

Từ giờ hệ thống sẽ tự động thức giấc mỗi 30 phút để kiểm tra tiến độ Phiên London, phân tích kết quả và tự khởi chạy vòng Training tiếp theo mà không cần Sếp phải can thiệp thủ công! 🤖"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
