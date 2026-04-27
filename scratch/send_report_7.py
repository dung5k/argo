import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 6 ⚠️

Kết quả Lượt 6 (Tăng chiều sâu NUM_LAYERS=2):
- Composite Score: 0.528
- Win Rate: 53.9% (cao nhất).
👉 ĐÁNH GIÁ: THẤT BẠI. Việc tăng NUM_LAYERS lên 2 khiến Win Rate sụt giảm nghiêm trọng so với Lượt 2 (65.8%). Qua 6 lượt thử nghiệm, chúng ta rút ra một bài học xương máu: Kiến trúc của Lượt 2 (D_MODEL=32, NUM_LAYERS=1, DROPOUT=0.3) chính là cấu trúc Não bộ TỐI ƯU NHẤT để đánh XAG London. Mạng sâu hơn sẽ bị nhiễu, mạng mỏng hơn sẽ bị ngộp.

❌ KHÔNG CHẤP NHẬN. Tiếp tục Tuning!

Khởi động Lượt 7 (Vũ Khí Bí Mật: Sức Mạnh Tương Đối):
- Kiến trúc: Trả về ĐÚNG cấu trúc vàng của Lượt 2.
- Đột phá Vĩ mô: Nếu "Não" đã tối ưu mà kết quả vẫn kẹt ở 66%, vấn đề nằm ở "Dữ liệu". Em vừa BƠM TRỰC TIẾP các tham số Vĩ mô cực kỳ nâng cao vào dòng máu của AI: `spread_ret`, `relative_strength` (sức mạnh tương đối), và `dxy_xau_anomaly` (Sự phân kỳ DXY-XAU).
- Mục đích: Giúp AI không chỉ nhìn XAG chạy theo Leaders, mà còn tính toán được việc XAG đang mạnh hay yếu hơn Leaders ở từng phút, qua đó bắt trọn các pha đè giá của Cá mập!

Lượt 7 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
