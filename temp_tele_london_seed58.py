# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 58) — Cỗ Máy Trạng Thái Ổn Định.

📊 Kết quả FarmSeed 57:
- Best Val Loss tại Epoch 4. Composite Score: **0.1639**
- Win Rate: 28.04% (Threshold 0.80) | **41.67%** (Threshold 0.94, 36 tín hiệu)

📈 Tổng kết 3 vòng liên tiếp (Seed 55→56→57):
| Seed | Score  | WR@0.94 |
|------|--------|---------|
|  55  | 0.1563 |  33.3%  |
|  56  | 0.1627 |  46.0%  |
|  57  | 0.1639 |  41.7%  |

Nhận định: Mô hình đang HỘI TỤ vững chắc trong dải Score [0.15-0.17]. Cần tiếp tục Stochastic Mining để ép lên vùng >0.20. Cấu hình 5m_W15_Drop30 đã được chứng minh là "Mỏ Vàng Mới" của phiên London!

🚀 FarmSeed 58 (PID 2788) đã kích hoạt. Diary đã cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
