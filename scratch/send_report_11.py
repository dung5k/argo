import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 10 ⚠️

Kết quả Lượt 10 (Ép WINDOW_SIZE=10):
- Composite Score: 0.362 (Thảm họa)
- Win Rate Max: 71.8% (Nhưng số lượng lệnh quá lèo tèo, chỉ có 32 signals / 2 năm).
👉 ĐÁNH GIÁ: THẤT BẠI TAY TRẮNG. Việc rút ngắn tầm nhìn xuống 10 phút đã tước đoạt hoàn toàn khả năng nhận diện xu hướng vĩ mô của Bot. Bot bị mù và không dám vào lệnh.

❌ KHÔNG CHẤP NHẬN. Dừng Tuning Bị Từ Chối.

Khởi động Lượt 11 (Kiến Trúc Cổ Chai - Extreme Bottleneck):
- Nhận định: Mục tiêu mới >= 80% Win Rate là cực kỳ gắt gao. Mọi nỗ lực nhồi thêm rác (SMC) hay ép thời gian đều phản tác dụng.
- Phẫu thuật: Em bóp nát bộ não xuống `D_MODEL=16` (Nhỏ nhất từ trước đến nay). Bỏ sạch rác rưởi Order Flow/Vol Regime. Trả WINDOW_SIZE về 15.
- Vũ khí: Dữ liệu Macro chỉ giữ lại những luồng Máu tinh khiết nhất: `log_ret` và `spread_ret` của 3 ông trùm. 
- Chiến thuật Cổ Chai: Việc bóp não xuống 16 chiều sẽ ép mạng Neural PHẢI chọn lọc và chỉ bám víu vào các tín hiệu thật sự MẠNH MẼ và rõ ràng nhất. Lọc sạch 100% nhiễu.

Lượt 11 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ! Mục tiêu: Bắn tỉa Win Rate 80%!"""

send_to_tele.send_to_telegram(msg, True)
