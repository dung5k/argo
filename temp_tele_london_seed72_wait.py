# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 72).

📊 Kết quả FarmSeed 71:
- Best Val Loss tại Epoch 2. Composite Score: 0.1729
- Win Rate: 28.69% (Threshold 0.80) | 50.0% (Threshold 0.94)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  66  | **0.1826** |  **29.63%** |  45.0%  |
|  67  | 0.1698 |  27.71% |  47.2%  |
|  68  | 0.1692 |  28.50% |  50.0%  |
|  69  | 0.1700 |  27.00% |  51.3%  |
|  70  | 0.1379 |  28.48% |  45.1%  |
|  71  | 0.1729 |  28.69% |  50.0%  |

Cú "Bounce Back" ngoạn mục! Score đã bật nảy cực mạnh từ 0.1379 về lại vùng cao 0.1729. Tín hiệu cân bằng tốt hơn đáng kể. 🚀 FarmSeed 72 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
