import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 14 ⚠️

Kết quả Lượt 14 (Tầm nhìn dài hạn WINDOW=30):
- Composite Score: 0.465
- Win Rate Max: Tụt dốc thê thảm xuống còn 53.0%
👉 ĐÁNH GIÁ: THẤT BẠI HOÀN TOÀN. Lý thuyết "Tầm nhìn dài hạn" đã sụp đổ. Việc giãn khung thời gian ra 30 phút đã ôm vào quá nhiều dữ liệu rác, khiến Bot bị "tẩu hỏa nhập ma" và đánh mất độ sắc bén của Lượt 13. Tầm nhìn 15 phút chính thức là vùng đất Thánh không thể xâm phạm!

❌ KHÔNG CHẤP NHẬN. Tiếp tục Tuning!

Khởi động Lượt 15 (THỨC TỈNH TIỀN SỐ - Crypto Awakening):
- Triết lý: Kiến trúc (Não bộ) và Khung thời gian (15 phút) đã đạt độ hoàn hảo tối đa. Để bứt phá lên đỉnh 80% Win Rate, chúng ta CẦN MỘT LĂNG KÍNH VĨ MÔ MỚI.
- VŨ KHÍ TỐI THƯỢNG: Nạp thẳng Bitcoin (`BTCUSDm`) vào làm Chỉ số Dẫn dắt (Leader) thứ 4! 
- Lý do: Bitcoin hiện nay là Phong vũ biểu (Barometer) cực nhạy cho "Khẩu vị rủi ro" của giới Smart Money toàn cầu. Trước khi dòng tiền ồ ạt đổ vào Vàng/Bạc hay Chứng khoán, nó thường "test nước" ở mảng Tiền số trước. Việc có Bitcoin đóng vai trò như Radar cảnh báo sớm kết hợp với 4-Heads (`N_HEAD=4`) sẽ giúp con Bot này sở hữu năng lực đánh chặn (front-run) mạnh nhất từ trước tới nay.

Lượt 15 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ! Mục tiêu: 80% Win Rate hoặc Không Gì Cả!"""

send_to_tele.send_to_telegram(msg, True)
