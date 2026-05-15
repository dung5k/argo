# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Báo cáo tình hình: Ổn định — FarmSeed 56 đang chạy ngầm.

📊 Trạng thái hiện tại:
- FarmSeed 56 (PID 3524) đã được kích hoạt từ chu kỳ trước và đang trong giai đoạn tiền xử lý Tensor + những Epoch đầu tiên.
- Thư mục results/ chưa được tạo → mô hình chưa hoàn thành Epoch đầu tiên.
- Cỗ Máy Trạng Thái đang trong chế độ giám sát — giữ nguyên hàng rào chống Concurrency.

Chu kỳ tiếp theo (30 phút sau) sẽ đọc kết quả và quyết định tiếp tục khai thác hay chuyển sang Seed 57. 🔄"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
