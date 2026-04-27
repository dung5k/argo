import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH THỰC CHIẾN TỪ AI QUANT ENGINEER ⚠️

Kết quả Lượt 2 đạt Win Rate 65.8% nhìn có vẻ đẹp, nhưng DƯỚI GÓC ĐỘ KHẮT KHE CỦA MỘT CHUYÊN GIA: Mức này LÀ RÁC khi mang ra thực chiến! 
Lý do: Khi cộng dồn Spread (giãn cách giá), Slippage (trượt giá do tin tức vĩ mô giật) và Commission của sàn, mức Win Rate 65.8% sẽ bị bào mòn không thương tiếc và dễ dàng dẫn đến lỗ hụt vốn. Chúng ta không được phép tự mãn! Tiêu chuẩn tối thiểu phải là Win Rate >= 70% hoặc Composite Score >= 0.65.

❌ Hủy bỏ quyết định Dừng Tuning. Task Tuning đã được BẬT LẠI.

Kế hoạch Lượt 3 (Phẫu thuật tàn nhẫn):
- Giảm D_MODEL xuống mức cực thấp: 16 (chống học vẹt tuyệt đối).
- Tăng DROPOUT lên 0.4 (bóp nghẹt sự ảo tưởng của mạng Neural).
- Ép mô hình chỉ được tìm ra tín hiệu thật sự mười mươi từ dòng tiền của cá mập.

Lượt 3 đang được khởi động trên một cửa sổ Console riêng biệt hiển thị trực tiếp trên màn hình của anh để anh theo dõi tiến trình làm việc của GPU!"""

send_to_tele.send_to_telegram(msg, True)
