import sys
import os
sys.path.append(os.path.abspath('.agent'))
from send_to_tele import send_to_telegram

msg = """
✅ **THIẾT LẬP AUTO-TUNING LTC NEW YORK THÀNH CÔNG**

Dạ Sếp, em đã hoàn thành việc thiết lập chiến thuật đào tạo tự động cho Phiên Mỹ (NY) của cặp LTCUSDT. 

1️⃣ **Prompt Chiến thuật:** File `periodic_prompt_ltc_ny_v5_local.md` đã sẵn sàng với bộ quy tắc sát thủ:
- Đặc thù phiên Mỹ: Biến động mạnh, nổ thanh khoản, nhiều fakeout đầu phiên.
- Mục tiêu nhắm tới: TP 0.5% / SL 0.4%, bộ lọc nến nhanh (FAST_HIT=5).
- Data Diet: Giới hạn chỉ dùng BTC và ETH làm điểm neo vĩ mô.

2️⃣ **Tác vụ Định kỳ:** Task `ltc_ny_v5_auto_tuning` đã được **BẬT (Enabled)** trong hệ thống ngầm. Hệ thống sẽ bắt đầu tự động bốc dữ liệu lên và tiến hành huấn luyện các bộ não LTC cho phiên NY bắt đầu từ hôm nay. Kết quả (Score/WR) sẽ được bot báo cáo liên tục mỗi khi chốt xong 1 kỷ lục mới ạ!
"""

sys.argv = ['send_to_tele.py', msg.strip(), '--channel', '1816854047', '--done']
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("message")
parser.add_argument("--channel", type=str)
parser.add_argument("--done", action="store_true")
args = parser.parse_args()

send_to_telegram(args.message, args.done, args.channel)
