import sys
import os
sys.path.append(os.path.abspath('.agent'))
from send_to_tele import send_to_telegram

msg = """
🦅 **[New York V5] AUTO-TUNING RUN MỚI KHỞI ĐỘNG**

Dạ Sếp, hệ thống tự động đã phân tích kết quả Run 21 và phát hiện việc nới lỏng thời gian (FH=12) không hiệu quả. Vì vậy, em đã loại bỏ nó và kích hoạt Run 22 mới:

- **Run ID:** `run_20260508_130000_v5_ny_gamma15`
- **Ý tưởng:** Trở về nguyên bản cấu hình "Chén Thánh" (Hard Label, LR=3e-5, FH=8). Lần này em nới lỏng mức phạt Focal Loss (giảm Gamma từ 2.0 xuống 1.5).
- **Mục tiêu:** Kích thích mô hình tự tin ra lệnh nhiều hơn (đạt N>100) mà vẫn giữ nguyên được độ tinh khiết (Score > 0.75).
- **Best so far:** Score 0.7730, WR 100% (Run 20).

Quá trình huấn luyện đang chạy ngầm rồi ạ!
"""

sys.argv = ['send_to_tele.py', msg.strip(), '--channel', '1816854047']
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("message")
parser.add_argument("--channel", type=str)
parser.add_argument("--done", action="store_true")
args = parser.parse_args()

send_to_telegram(args.message, args.done, args.channel)
