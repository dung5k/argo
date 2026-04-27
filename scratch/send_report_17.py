import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 16 ⚠️

Kết quả Lượt 16 (Thức Tỉnh Tiền Số):
- Composite Score: 0.325 (Rớt thê thảm)
- Win Rate Max: Chỉ lẹt đẹt ở 55.8%
👉 ĐÁNH GIÁ: THẤT BẠI NẶNG NỀ. Dữ liệu thực chiến đã tát một cú trời giáng vào lý thuyết của em. Bitcoin KHÔNG HỀ giúp ích gì cho Bạc (XAG). Ngược lại, những pha giật lag điên cuồng của Crypto đã nhồi nhét một rổ "Rác" (Noise) vào bộ não AI, khiến Win Rate sụp đổ từ 64% xuống còn 55%. XAG chỉ là "đàn em" của Vàng và DXY, chấm hết!

❌ TỪ CHỐI KẾT QUẢ. Phải phẫu thuật sâu hơn!

Khởi động LƯỢT 17 (BỘ NÃO KHẮC KỶ - The Stoic Brain):
- Quyết định 1: Gạch tên Bitcoin vĩnh viễn khỏi danh sách. Trả lại 3 Leaders nguyên thủy (XAU, DXY, USTEC).
- Quyết định 2 (ĐỘT PHÁ LỊCH SỬ): Nếu XAG chỉ là kẻ chạy theo Leaders, vậy các chỉ báo Phân tích Kỹ thuật (TA) của bản thân XAG là VÔ DỤNG và CHẬM TRỄ!
- Hành động: Em đã kích hoạt cơ chế `ZERO_NOISE_TARGET` (vừa được code thẳng vào Core hệ thống). Nó sẽ TÀN SÁT VÀ XOÁ SẠCH toàn bộ các chỉ báo kỹ thuật rườm rà (RSI, MACD, Bollinger Bands, Bóng nến, Doji...) của bản thân mã XAG. Chỉ giữ lại đúng 3 luồng sinh khí: Giá, Khối lượng và Spread.
- Mục tiêu: Bằng cách "bịt mắt" Bot khỏi những biến động nội tại rác rưởi của XAG, nó sẽ bị ÉP BUỘC phải nhìn 100% vào Vĩ mô (Vàng, Đô La) để ra quyết định. 

Lượt 17 mang theo một bộ não thanh tịnh và sắc bén nhất đang được bùng cháy trên Console của anh! Lần này phải xuyên thủng 80% Win Rate!"""

send_to_tele.send_to_telegram(msg, True)
