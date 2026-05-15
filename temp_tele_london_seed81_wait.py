# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 81).

📊 Kết quả FarmSeed 80:
- Best Val Loss tại Epoch 2. Composite Score: 0.1114
- Win Rate: 25.51% (Threshold 0.78) | 45.45% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  76  | 0.1190 |  27.02% |  45.1%  |
|  77  | 0.1662 |  26.44% |  54.0%  |
|  78  | 0.1216 |  26.17% |  45.1%  |
|  79  | 0.1168 |  25.03% |  52.8%  |
|  80  | 0.1114 |  25.51% |  45.4%  |

Score tiếp tục rớt đáy! Val Loss không đổi nhưng Win Rate cực đại giảm nhẹ và lỗi mất cân bằng (thiên vị Buy) vẫn tồn tại. Hệ thống đang kẹt rất sâu trong vùng nhiễu này. 🚀 FarmSeed 81 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
