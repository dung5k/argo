# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 04:58:00] - Lượt đánh giá Run: run_20260504_035800_v3_asian_auto_104 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Thất bại của Run 104 cho thấy việc bổ sung bối cảnh 4 giờ (Deep MTF) không mang lại hiệu quả tức thì, thậm chí có thể làm loãng đi các tín hiệu vi mô của phiên Á. Trong một thị trường thanh khoản thấp, các xu hướng dài hạn (4h) có thể quá chậm chạp để AI ra quyết định chính xác cho các lệnh giữ trong 20 nến (45 phút/nến). 
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Lập tức dispatch **Run 105** (Zero Noise + Deep MTF) để xem liệu việc "thanh lọc nhãn" có cứu vãn được bối cảnh đa khung hay không.
    2. Chuẩn bị **Run 106** với chiến thuật **"Thanh tẩy Macro" (Macro Purge)**.
    3. Loại bỏ hoàn toàn **DXYm, XAUUSDm** để AI không bị xao nhãng bởi các chỉ báo tài chính truyền thống vốn ít biến động trong phiên Á.
    4. Tăng **D_MODEL lên 128** để tạo không gian suy luận rộng hơn cho các đặc trưng Crypto thuần túy (Price + Order Flow + LTCBTC).
    5. Quay lại **MTF [15, 60]** (loại bỏ 240).
- **Giả thuyết (Hypothesis):** Trong phiên Á, Crypto thường vận hành theo "luật chơi" nội bộ (Rotation/Order Flow) hơn là bị dẫn dắt bởi Macro. Việc loại bỏ các biến Macro nhiễu và tăng độ rộng mô hình (D_MODEL 128) sẽ giúp AI tập trung 100% tài nguyên để giải mã các "mật mã" dòng tiền giữa LTC và BTC. Sự tinh khiết này hy vọng sẽ mang lại một bước nhảy vọt về Win Rate.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
