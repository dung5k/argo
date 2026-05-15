# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 64).

📊 Kết quả FarmSeed 63:
- Best Val Loss tại Epoch 3. Composite Score: 0.1370
- Win Rate: 28.61% (Threshold 0.80) | 53.13% (Threshold 0.93)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  58  | 0.1754 |  28.41% |  53.1%  |
|  59  | 0.1810 |  29.42% |  53.1%  |
|  60  | 0.1664 |  30.94% |  50.0%  |
|  61  | 0.1747 |  28.59% |  50.0%  |
|  62  | 0.1701 |  29.01% |  45.7%  |
|  63  | 0.1370 |  28.61% |  53.1%  |

FarmSeed 64 (PID 15512) đang tiếp tục được đào tạo, hiện tại đang ở giai đoạn đầu. 🚀 FarmSeed 64 (PID 15512) đã bùng cháy! Mục tiêu: Phá kỷ lục 0.1810!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
