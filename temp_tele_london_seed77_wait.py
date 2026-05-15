# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 77).

📊 Kết quả FarmSeed 76:
- Best Val Loss tại Epoch 6. Composite Score: 0.1190
- Win Rate: 27.02% (Threshold 0.79) | 45.16% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  71  | 0.1729 |  28.69% |  50.0%  |
|  72  | 0.1304 |  26.41% |  38.8%  |
|  73  | 0.1214 |  25.00% |  52.0%  |
|  74  | 0.1338 |  27.42% |  55.0%  |
|  75  | 0.1199 |  25.97% |  44.1%  |
|  76  | 0.1190 |  27.02% |  45.1%  |

Hệ thống vẫn đang dao động dò dẫm trong "Vùng Tối" của Local Minima do mất cân bằng lệnh (thiên vị lệnh Buy quá mạnh). Tuy nhiên Val Loss vẫn siêu cứng ở 0.5013! 🚀 FarmSeed 77 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
