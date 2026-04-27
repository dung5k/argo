import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 8 ⚠️

Kết quả Lượt 8 (Nới rộng Não D_MODEL=48):
- Composite Score: Thảm họa 0.393
- Win Rate Max: 62.5%
👉 ĐÁNH GIÁ: THẤT BẠI. Rõ ràng là dữ liệu của XAG không hề phù hợp với một mạng nơ-ron lớn. Việc tăng D_MODEL lên 48 khiến mô hình bị Underfit nghiêm trọng. D_MODEL=32 là ranh giới tuyệt đối!

❌ KHÔNG CHẤP NHẬN. Dừng Tuning Bị Từ Chối.

Khởi động Lượt 9 (Điểm Rơi Lý Tưởng + Kỷ Luật Thép):
- Kiến trúc: Khóa chặt lại ở D_MODEL=32 (Não 32) và NUM_LAYERS=1.
- Dữ liệu: Giữ lại sức mạnh Vĩ mô từ Lượt 7 (`spread_ret`, `relative_strength`).
- Đột phá (Kỷ luật thép): Em đã TĂNG CỰC MẠNH hệ số DROPOUT lên 0.4 (từ 0.3). Vì ở Lượt 7, mô hình đạt WR 68.4% nhưng Score thấp do bị học vẹt. Mức Dropout 0.4 sẽ giáng những cú đấm cực mạnh vào mạng nơ-ron trong lúc học, ép nó phải tự tìm ra bản chất của Dòng Tiền thực sự thay vì nhớ vẹt các tín hiệu nhiễu!

Lượt 9 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
