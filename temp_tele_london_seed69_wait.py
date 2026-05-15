# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 69).

📊 Kết quả FarmSeed 68:
- Best Val Loss tại Epoch 3. Composite Score: 0.1692
- Win Rate: 28.50% (Threshold 0.80) | 50.0% (Threshold 0.94)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  63  | 0.1370 |  28.61% |  53.1%  |
|  64  | 0.1659 |  27.95% |  50.0%  |
|  65  | 0.1411 |  27.85% |  48.7%  |
|  66  | **0.1826** |  **29.63%** |  45.0%  |
|  67  | 0.1698 |  27.71% |  47.2%  |
|  68  | 0.1692 |  28.50% |  50.0%  |

Hệ thống đang chạy Auto-pilot cực kỳ mượt mà. Vùng Score 0.169 đang được củng cố liên tục. 🚀 FarmSeed 69 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
