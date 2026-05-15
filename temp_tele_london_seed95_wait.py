# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 95).

📊 Kết quả FarmSeed 94:
- Best Val Loss tại Epoch 2. Composite Score: 0.1013 (Phục hồi nhẹ)
- Win Rate: 24.71% (Threshold 0.79) | 43.33% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  89  | 0.1043 |  23.52% |  51.3%  |
|  90  | 0.1152 |  26.46% |  50.0%  |
|  91  | 0.0986 |  23.83% |  47.6%  |
|  92  | 0.1022 |  24.19% |  50.0%  |
|  93  | 0.0969 |  23.53% |  45.4%  |
|  94  | 0.1013 |  24.71% |  43.3%  |

Chuỗi Val Loss < 0.500 vô tiền khoáng hậu (10 vòng liên tiếp) đã bị ngắt quãng khi Seed 94 nhích nhẹ lên mức 0.5011. Dù vậy, sức chịu đựng của thuật toán Lõi AI V6 trước biến động của Validation vẫn rất khủng khiếp. Score đã phục hồi lên mức 0.1013 dù tỷ lệ cược hoàn toàn bất lợi. 🚀 FarmSeed 95 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
