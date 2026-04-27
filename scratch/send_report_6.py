import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 5 ⚠️

Kết quả Lượt 5 (Bật full dấu chân SMC):
- Composite Score: THẢM HOẠ 0.274
- Win Rate: Chỉ lẹt đẹt ở mức 53.8%.
👉 ĐÁNH GIÁ: Một sai lầm chiến thuật. Việc bật CẢ 2 tính năng 'VOL_REGIME' và 'ORDER_FLOW' trong khi bóp Learning Rate quá nhỏ (5e-6) và giữ mạng Neural cực mỏng (1 Layer) đã khiến AI bị ngộp. Nó giống như việc bắt một đứa trẻ giải phương trình vi phân vậy. Mạng nơ-ron không đủ không gian để nén khối lượng dữ liệu phức tạp này.

❌ KHÔNG CHẤP NHẬN. Tiếp tục Tuning!

Khởi động Lượt 6 (Điểm Ngọt Kiến Trúc):
- Trả lại sự đơn giản: CHỈ sử dụng ORDER_FLOW (Tắt VOL_REGIME để giảm nhiễu).
- Cấu trúc: Giữ D_MODEL=32 nhưng TĂNG CHIỀU SÂU (NUM_LAYERS=2). 2 Lớp sẽ giúp mô hình có khả năng học các logic bậc cao (phi tuyến tính) của Dòng tiền mà không làm phình to băng thông đầu vào.
- Trả Learning Rate về chuẩn 1e-5.

Mục tiêu không đổi: Tối thiểu WR 70% hoặc Score 0.65!
Lượt 6 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
