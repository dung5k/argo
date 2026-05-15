# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 56) - Cỗ Máy Trạng Thái Ổn Định.

📊 Kết quả FarmSeed 55:
- Early Stopping tại Epoch 92. Best Val Loss chốt tại Epoch 22.
- Composite Score: **0.1563** (↑ đột phá so với Seed 52: 0.0463!)
- Win Rate: 26.71% (Threshold 0.80) | **33.33%** (Threshold 0.94)
- Phân tích: Tín hiệu RẤT TÍCH CỰC! Sau khi chuyển sang 5m_W15_Drop30, mô hình đã thoát hẳn khỏi trạng thái Overfit. Composite Score vọt tăng x3 lần so với mức đáy. Cấu hình này xứng đáng được tiếp tục khai thác.

🚀 Triển khai FarmSeed 56:
- Giữ nguyên bộ gen "Vàng" mới: 5m, W15, Dropout=0.30, LR=5e-5, D_MODEL=64
- PID: 3524 đang chạy ngầm.
- Diary đã được cập nhật.

Tiếp tục cày ải để ép Composite Score vượt mốc 0.20+! 🎯"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
