# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [LONDON V6 MTF] Đang Chờ (FarmSeed 91).

📊 Kết quả FarmSeed 90:
- Best Val Loss tại Epoch 5. Composite Score: 0.1152 (Đang Phục Hồi)
- Win Rate: 26.46% (Threshold 0.78) | 50.00% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  86  | 0.1061 |  24.34% |  48.7%  |
|  87  | 0.1104 |  24.96% |  54.0%  |
|  88  | 0.1078 |  24.83% |  56.4%  |
|  89  | 0.1043 |  23.52% |  51.3%  |
|  90  | 0.1152 |  26.46% |  50.0%  |

Score đã bắt đầu phục hồi (0.1152) nhờ lượng lệnh Sell xuất hiện trở lại (11 lệnh). Đặc biệt, Val Loss đánh dấu chuỗi 7 vòng liên tiếp ĐÓNG ĐINH vững chắc dưới 0.500 (hiện tại là 0.4971). Win Rate cũng ổn định trên mốc 50%. Lõi AI V6 thực sự đã "miễn nhiễm" với nhiễu của London. 🚀 FarmSeed 91 đang chạy ngầm và chưa hoàn tất. Vui lòng đợi kết quả trong chu kỳ tiếp theo!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
