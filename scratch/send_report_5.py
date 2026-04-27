import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THỰC TRẠNG MÔ HÌNH (LƯỢT 4) ⚠️

Kết quả Lượt 4 (WINDOW=30, D_MODEL=32):
- Composite Score: 0.566
- Win Rate: 66.6% (với 33 tín hiệu).
👉 ĐÁNH GIÁ: Tạm ổn nhưng VẪN LÀ RÁC nếu xét theo tiêu chuẩn Khắt khe (WR >= 70% hoặc Score >= 0.65). Việc tăng Window lên 30 phút dường như làm AI phản ứng hơi trễ so với nhịp giật của XAG. Window 15 phút ở Lượt 2 vẫn cho ra Score (0.59) tốt hơn.

❌ KHÔNG CHẤP NHẬN. DỪNG TUNING BỊ TỪ CHỐI.

Khởi động Lượt 5 (Tổ hợp SMC Hoàn chỉnh):
- Rút ngắn WINDOW_SIZE về 15 phút (nhanh, chớp nhoáng).
- Kiến trúc mỏng: D_MODEL=32, NUM_LAYERS=1.
- Vũ khí hạng nặng: Bật CẢ 2 dấu chân 'ORDER_FLOW' và 'VOL_REGIME' để AI phân biệt chính xác đâu là pha nổ vol thật, đâu là pha rút râu quét thanh khoản.
- Ép Learning Rate xuống 5e-6 để tìm kiếm chính xác cực độ.

Lượt 5 đang được kích hoạt và mở thẳng cửa sổ Console trên màn hình để anh kiểm tra GPU!"""

send_to_tele.send_to_telegram(msg, True)
