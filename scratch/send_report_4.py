import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THỰC TRẠNG MÔ HÌNH (LƯỢT 3) ⚠️

Kết quả Lượt 3 (D_MODEL=16, DROPOUT=0.4):
- Composite Score: Rơi tự do xuống 0.337
- Win Rate: Chỉ đạt 56% ở số lượng tín hiệu quá ít (41 lệnh).
👉 ĐÁNH GIÁ: THẤT BẠI THẢM HẠI. Việc bóp nghẹt mạng nơ-ron quá đáng (cắt giảm xuống 16) đã khiến AI bị UNDERFIT (không đủ năng lực để học quy luật của dòng tiền). Nó hoàn toàn bị mù trước các pha quét thanh khoản.

Khởi động Lượt 4 (Tìm điểm cân bằng):
- Cấu hình mạng: Quay về D_MODEL=32 (Mức đã chứng minh được năng lực ở Lượt 2).
- Tầm nhìn: Tăng WINDOW_SIZE từ 15 lên 30. Việc 15 phút là quá ngắn để AI đo lường được xung lượng của tin tức từ DXY/Nasdaq truyền sang XAG. 30 phút sẽ cho nó góc nhìn vĩ mô rộng hơn một chút.
- Mục tiêu: Bắt buộc phá vỡ mốc Win Rate 70% và Score 0.65!

Lượt 4 đang được kích hoạt và sẽ sớm hiện lên cửa sổ Console trên màn hình của anh!"""

send_to_tele.send_to_telegram(msg, True)
