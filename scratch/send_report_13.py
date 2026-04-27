import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 12 ⚠️

Kết quả Lượt 12 (Chỉ dùng Vàng làm Leader):
- Composite Score: 0.467
- Win Rate Max: Lẹt đẹt ở 50.0%
👉 ĐÁNH GIÁ: THẤT BẠI DIỆT VONG. Việc em loại bỏ DXY và Nasdaq ra khỏi thuật toán đã khiến Win Rate sụp đổ từ 68% xuống còn 50%. Điều này đã chứng minh một sự thật đắt giá: Mặc dù Vàng là kim chỉ nam, nhưng Bạc (XAG) KHÔNG THỂ giao dịch chính xác nếu thiếu đi sức mạnh của đồng Đô La (DXY) và Khẩu vị rủi ro (Nasdaq)!

❌ KHÔNG CHẤP NHẬN. Tiếp tục Tuning!

Khởi động Lượt 13 (ĐA GÓC NHÌN - 8 Head Attention):
- Triết lý: Nếu XAG phụ thuộc vào cả 3 ông trùm (XAU, DXY, USTEC), thì bộ não của nó phải đủ sắc bén để "nhìn" cả 3 ông cùng một lúc mà không bị loạn.
- Tùy chỉnh: Em giữ nguyên Não Vàng `D_MODEL=32` (tránh bị underfit), khôi phục lại ĐẦY ĐỦ 3 mã Leader.
- VŨ KHÍ BÍ MẬT: Em TĂNG SỐ LƯỢNG MẮT (Attention Heads) từ 2 lên 8! (`N_HEAD=8`).
- Mục đích: 8 cái đầu (Heads) này sẽ chịu trách nhiệm phân tách rành mạch từng luồng tín hiệu (Head 1 soi DXY, Head 2 soi XAU, Head 3 soi Order Flow...). Chúng sẽ không bị trộn lẫn và giẫm đạp lên nhau như khi chỉ có 2 Heads. Kỹ thuật này sẽ ép AI chắt lọc được sự giao thoa tinh vi nhất để vươn tới mốc Win Rate 80%!

Lượt 13 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
