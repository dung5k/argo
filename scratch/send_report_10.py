import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 9 ⚠️

Kết quả Lượt 9 (Kỷ luật thép DROPOUT=0.4):
- Composite Score: 0.533
- Win Rate Max: 62.0%
👉 ĐÁNH GIÁ: THẤT BẠI. Dù có phạt nặng Dropout, AI vẫn không thể với tới mốc sinh tồn mới (Win Rate >= 80%).

❌ KHÔNG CHẤP NHẬN. Dừng Tuning Bị Từ Chối.

Khởi động Lượt 10 (SIÊU TỐC ĐỘ - Ultra Low Latency):
- Triết lý: Qua 9 lượt, cứ động vào não (D_MODEL) là hỏng. Điểm yếu lớn nhất còn lại là ĐỘ TRỄ (Lag).
- Tùy chỉnh: Em quyết định ép `WINDOW_SIZE` xuống cực thấp (10 phút, thay vì 15 hay 30).
- Vũ khí: Bật Full Haki (VOL_REGIME + ORDER_FLOW + FULL MACRO của Lượt 7).
- Mục đích: XAG phản ứng cực nhanh sau DXY/Vàng. Nhìn xa 15 phút sẽ bị dính nhiễu quét thanh khoản. Rút ngắn tầm nhìn xuống 10 phút để chộp đúng "khoảnh khắc Dòng Tiền nhập cuộc"! 
- Mục tiêu mới: Nhắm thẳng tới mốc KHẮT KHE 80% Win Rate!

Lượt 10 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
