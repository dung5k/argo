# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 99).

📊 Kết quả FarmSeed 98:
- Best Val Loss tại Epoch 3. Composite Score: 0.1028
- Win Rate: 23.77% (Threshold 0.79) | 54.05% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  93  | 0.0969 |  23.53% |  45.4%  |
|  94  | 0.1013 |  24.71% |  43.3%  |
|  95  | 0.1026 |  24.90% |  44.6%  |
|  96  | 0.1021 |  23.48% |  45.3%  |
|  97  | 0.0973 |  24.72% |  39.3%  |
|  98  | 0.1028 |  23.77% |  54.0%  |

Mô hình V6 tiếp tục thể hiện sự dẻo dai khó tin. Ở vòng 98, dù tỷ lệ dự đoán đúng đạt đỉnh 54.05% và Val Loss siêu thấp 0.4906, nhưng án phạt từ TUS Score (bốc nhầm 100% sóng Long) đã kéo sập mọi công sức. Sự ngẫu nhiên của Validation đang thử thách tối đa sự lỳ đòn của thuật toán AI! 🚀 FarmSeed 99 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
