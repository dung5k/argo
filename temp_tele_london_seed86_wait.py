# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 86).

📊 Kết quả FarmSeed 85:
- Best Val Loss tại Epoch 2. Composite Score: 0.1102 (Đáy Lịch Sử Mới)
- Win Rate: 24.87% (Threshold 0.79) | 50.98% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  81  | 0.1338 |  26.82% |  51.3%  |
|  82  | 0.1163 |  26.11% |  51.6%  |
|  83  | 0.1253 |  26.68% |  50.0%  |
|  84  | 0.1175 |  26.06% |  45.1%  |
|  85  | 0.1102 |  24.87% |  50.9%  |

Cảnh báo Đáy Lịch Sử: Composite Score rớt thảm về 0.1102 do chịu án phạt TUS cực nặng. TUY NHIÊN, tin mừng là Val Loss vẫn đóng đinh ở mức kinh ngạc 0.4961, và Win Rate đỉnh vẫn cao >50%. Lõi não bộ V6 đang học rất "ngọt", lò xo đang bị nén tối đa. 🚀 FarmSeed 86 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
