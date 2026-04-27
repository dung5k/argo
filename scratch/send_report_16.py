import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO SỰ CỐ LƯỢT 15 ⚠️

Em xin báo cáo khẩn: Lượt 15 (Crypto Awakening) đã BỊ CRASH và huỷ bỏ ngay từ vòng gửi xe!
- Nguyên nhân: Việc thêm `BTCUSDm` vào dữ liệu yêu cầu Bot phải cào dữ liệu từ Exness. Quá trình cào đã thành công, nhưng hệ thống Load Data lại dính lỗi do file cấu hình gốc đang trỏ nhầm sang thư mục của phiên NY (`workspaces/CFG_XAG_NY_V3_5`) thay vì LDN. 
- Hậu quả: Quá trình ghép Tensor thất bại hoàn toàn. Lượt 15 không thể huấn luyện.

✅ KHẮC PHỤC: Em đã trực tiếp phẫu thuật mã nguồn (`base_config.json`) và vá lỗ hổng này.

Khởi động LƯỢT 16 (Làm lại Lượt 15 - Thức Tỉnh Tiền Số):
- Cấu trúc hoàn toàn giống Lượt 15: `WINDOW_SIZE=15`, `N_HEAD=4`, nạp đầy đủ Radar `BTCUSDm`.
- Mục tiêu không đổi: Tận dụng Bitcoin làm cảnh báo sớm để lột xác Win Rate chạm mốc 80%!

Lượt 16 đang được kích hoạt và đẩy lên màn hình Console của anh ngay bây giờ!"""

send_to_tele.send_to_telegram(msg, True)
