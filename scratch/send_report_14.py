import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 13 ⚠️

Kết quả Lượt 13 (Đa Góc Nhìn N_HEAD=8):
- Composite Score: 0.448
- Win Rate Max: 64.5% (Tăng vượt bậc so với Lượt 12)
👉 ĐÁNH GIÁ: THÀNH CÔNG MỘT NỬA. Việc giữ lại 3 Leaders và trang bị 8-Heads cho Bot đã giúp nó bóc tách tín hiệu tốt hơn hẳn, kéo Win Rate từ 50% lên 64.5%. Tuy nhiên, điểm thắt nút cuối cùng ngăn cản mô hình chạm đỉnh 80% chính là "Tầm Nhìn" (WINDOW_SIZE=15). XAG có độ trễ nhất định so với Vàng/DXY. 15 phút chưa đủ để hình thành một xu hướng rõ rệt mà dễ bị dính bẫy quét thanh khoản.

❌ CHƯA ĐẠT CHỈ TIÊU (80%). Tiếp tục Tuning!

Khởi động Lượt 14 (TẦM NHÌN DÀI HẠN - Expanded Horizon):
- Triết lý: Nếu Bot đã có "Đa Góc Nhìn" (8 Heads) để phân tích sắc bén, thì việc tiếp theo là phải cung cấp cho nó một "Tầm Nhìn" đủ rộng để đưa ra phán đoán chắc nịch.
- Tùy chỉnh: Kéo giãn WINDOW_SIZE lên mốc tối đa cho phép là 30 phút (nửa tiếng). Bật thêm chỉ báo cấu trúc Vol Regime.
- Mục đích: Nửa tiếng là quãng thời gian lý tưởng để Dòng Tiền thực sự lộ diện sau khi tin tức Vĩ mô được tung ra. Sự kết hợp giữa bộ não 8-Heads phân tích siêu việt và khung cảnh Vĩ mô dài 30 phút được kỳ vọng là mũi đinh ba chí mạng để xuyên thủng rào cản 80% Win Rate!

Lượt 14 đang hừng hực bốc cháy trên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
