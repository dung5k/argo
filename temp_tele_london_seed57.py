# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 57) — Cỗ Máy Trạng Thái Ổn Định.

📊 Kết quả FarmSeed 56:
- Early Stopping tại Epoch 84. Best Val Loss tại Epoch 6.
- Composite Score: **0.1627** (ổn định, xác nhận cấu hình)
- Win Rate: 28.65% (Threshold 0.80) | **46.0%** (Threshold 0.94 — 50 tín hiệu cân bằng!)
- Phân tích: ĐÀY TRIỂN VỌNG! Khi lọc ở ngưỡng cao nhất 0.94, mô hình chọn lựa đúng gần 1 trong 2 lệnh. Cấu hình 5m_W15_Drop30 đang hội tụ về một vùng cực kỳ ổn định.

🚀 Triển khai FarmSeed 57:
- Tiếp tục khai thác bộ gen "Vàng Mới": 5m, W15, Drop=0.30, LR=5e-5
- PID: 14900 đang gầm rú dưới nền.
- Diary đã được cập nhật.

Mỗi Seed là một mẻ thăm dò — chúng ta đang ngày càng tiệm cận đỉnh cao! 🎯"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
