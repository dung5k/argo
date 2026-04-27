import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 7 ⚠️

(Xin lỗi anh, Lượt 7 vừa nãy đã chạy xong và Early Stop tại Epoch 478 nhưng không gửi được biểu đồ lên Telegram do khi đó code chưa nhận được bản vá lỗi Token Extension. Lỗi này đã được khắc phục hoàn toàn!)

Kết quả Lượt 7 (Bơm Vũ Khí Vĩ Mô):
- Composite Score: 0.547 (Tăng nhẹ so với Lượt 6).
- Win Rate Max: Chạm mốc 68.4% (Rất hứa hẹn, nhưng bị nhiễu nên rớt lại 60.5% ở Best Epoch).
👉 ĐÁNH GIÁ: THẤT BẠI. Dù WR đã tiệm cận mức 70%, nhưng việc bơm quá nhiều Feature phức tạp vào cái Não 32-chiều (D_MODEL=32) khiến AI bị "quá tải thông tin". Nó phân tích được Vĩ mô nhưng lại bị nhiễu.

❌ KHÔNG CHẤP NHẬN. Tiếp tục Tuning!

Khởi động Lượt 8 (Nới Rộng Não Bộ):
- Tinh gọn Feature: Giữ lại `spread_ret` cho Vàng/DXY và `relative_strength` cho Nasdaq. Loại bỏ các tính toán thừa thãi để giảm nhiễu.
- Kiến trúc: NỚI RỘNG Không gian tư duy (Tăng D_MODEL lên 48). Mức 48 sẽ giúp AI có thêm sức chứa để nạp các thông số SMC vĩ mô mà không bị loạn trí như mức 32.

Lượt 8 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ! (Từ lượt này biểu đồ sẽ được gửi đều đặn qua Bot)."""

send_to_tele.send_to_telegram(msg, True)
