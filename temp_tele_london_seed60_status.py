# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Báo cáo tình hình: Ổn định — FarmSeed 60 đang trong giai đoạn Warm-Up.

📊 Trạng thái hiện tại:
- FarmSeed 60 (PID 7776) đang ở giai đoạn **Warm-Up Autoencoder** (Epoch 2/10).
- Recon MSE Loss đang giảm dần (0.065→0.059) — dấu hiệu khởi động ổn định.
- Cỗ Máy đang hoạt động trơn tru, không có xung đột tài nguyên.

Chu kỳ tiếp theo sẽ đọc kết quả Seed 60 và so sánh với kỷ lục 0.1810 của Seed 59. 🔄"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
