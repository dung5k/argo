import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 11 ⚠️

Kết quả Lượt 11 (Ép xung não bộ D_MODEL=16):
- Composite Score: 0.297 (Thảm họa diệt vong)
- Win Rate Max: 43.3%
👉 ĐÁNH GIÁ: THẤT BẠI. Mạng lưới D_MODEL=16 đã trở thành một nút thắt cổ chai quá hẹp. AI bị "ngộp thở" và mất hoàn toàn khả năng tư duy. Cột mốc D_MODEL=32 chính là giới hạn vật lý không thể phá vỡ!

❌ KHÔNG CHẤP NHẬN. Dừng Tuning Bị Từ Chối.

Khởi động Lượt 12 (BỨC TƯỜNG VÀNG - The Gold Standard):
- Triết lý: Qua 11 lượt, ta thấy càng bóp méo Não Bộ thì AI càng ngu đi. Vấn đề không nằm ở Não, mà nằm ở độ "Sạch" của dữ liệu Vĩ mô!
- Nhận định: Bạc (XAG) thực chất chỉ là cái bóng của Vàng (XAU). Việc chúng ta cố nhồi nhét DXY và Nasdaq vào có thể đang làm "loãng" tín hiệu và sinh ra các chỉ báo giả (nhiễu).
- Hành động: LOẠI BỎ HOÀN TOÀN DXY và USTEC khỏi thuật toán! Từ giờ, AI sẽ CHỈ ĐƯỢC NHÌN VÀO VÀNG (XAUUSD) để ra quyết định. Bật lại toàn bộ công nghệ Smart Money (Order Flow, Vol Regime).
- Mục tiêu: Xem thử sức mạnh nguyên thủy của Vàng có đủ để kéo Win Rate của Bạc lên 80% hay không!

Lượt 12 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
