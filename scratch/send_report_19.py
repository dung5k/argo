import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """⚠️ BÁO CÁO THẨM ĐỊNH LƯỢT 18 ⚠️

Kết quả Lượt 18 (Thẩm thấu Lợi suất):
- Composite Score: 0.511
- Win Rate Max: 55%
👉 ĐÁNH GIÁ: THẤT BẠI. Dữ liệu thực tế cho thấy việc thêm VIX và US10Y đã phá hủy cấu trúc tín hiệu thay vì giúp ích!
👉 LÝ DO MẮC KẸT CỐT LÕI: Dữ liệu VIX và US10Y được kéo từ Yahoo Finance là dữ liệu Daily (D1) và forward-fill xuống khung M1. Điều này tạo ra một đường thẳng tắp ngang trên ma trận 1440 nến/ngày, không mang lại bất kỳ giá trị dự báo biến động nội ngày (Intra-day) nào cho AI. Mô hình bị quá tải bởi các tham số "chết".

🔥 KHỞI ĐỘNG LƯỢT 19: CÚ BẮN TỈA TỐI THƯỢNG (The Ultimate Sniper) 🔥
Em đã xâu chuỗi lại toàn bộ lịch sử 18 lượt Tuning và phát hiện ra **CHÉN THÁNH**: Lượt 10 từng chạm mốc 71.8% Win Rate với `WINDOW_SIZE=10`, còn Lượt 17 đã chứng minh sức mạnh của `ZERO_NOISE_TARGET`.
Lượt 19 sẽ là TỔNG HỢP TINH HOA của cả hai, cộng thêm vũ khí Order Flow:
1. **Quay về Nguồn Cội:** Gạch bỏ VIX và US10Y, giữ lại bộ 3 Leader chuẩn xác nhất: XAU, DXY, USTEC.
2. **Ký ức Cực Ngắn:** Ép `WINDOW_SIZE=10` (AI chỉ nhìn đúng 10 nến phản ứng tức thời).
3. **Mù Loà Tuyệt Đối:** Giữ nguyên `ZERO_NOISE_TARGET=True` (Bịt mắt hoàn toàn khỏi các chỉ báo kỹ thuật của Bạc).
4. **Bộ Não Tối Giản:** `D_MODEL=32`, `N_HEAD=2`, `NUM_LAYERS=1`, và tăng `DROPOUT=0.4` kịch trần để chống học vẹt.
5. **Dấu Chân Đội Lái:** Bật cả `ORDER_FLOW` và `VOL_REGIME` (Hướng 2) để bắt thanh khoản tức thời.

Lượt 19 đang lao đi với tốc độ của một Sniper. Lần này phải đục thủng 80% Win Rate hoặc cháy máy!!!"""

send_to_tele.send_to_telegram(msg, True)
