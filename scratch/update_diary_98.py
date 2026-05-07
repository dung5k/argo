import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = """
### [2026-05-04 00:58:00] - Lượt đánh giá Run: run_20260504_002800_v3_asian_auto_97 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Kiến trúc "khắc khổ" (D_MODEL=32) cũng không mang lại đột phá, chứng tỏ vấn đề không nằm ở dung lượng mô hình mà nằm ở chất lượng tín hiệu đầu vào (Signal-to-Noise ratio). Phiên Á với đặc thù thanh khoản mỏng đang biến các dữ liệu "Dòng lệnh" (Order Flow) thành những bẫy nhiễu nguy hiểm, khiến mô hình bị sa lầy dù kiến trúc có tinh gọn đến đâu.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Quay lại mốc **Baseline kỷ lục Run 77** (WR 73.5%) làm nền tảng.
    2. Loại bỏ hoàn toàn **ORDER_FLOW** (Tắt về False) để làm sạch tín hiệu đầu vào khỏi nhiễu thanh khoản.
    3. Kích hoạt **VOL_REGIME = true** để mô hình nhận diện được các trạng thái biến động đặc thù của phiên Á (Tích lũy vs Đột phá).
    4. Giữ nguyên: Window 45m, Residual CLS_HEAD, D_MODEL 64, N_HEAD 4.
- **Giả thuyết (Hypothesis):** Loại bỏ Order Flow sẽ giúp Attention Mechanism tập trung 100% vào các tương quan giá cốt lõi (Price Correlation) giữa LTC và các Leader Assets. Cơ chế VOL_REGIME sẽ cung cấp thêm "lớp lọc" về bối cảnh thị trường, giúp AI phân biệt được các đợt biến động thực sự. Hy vọng sự kết hợp giữa "Gốc rễ 77" và "Lọc biến động" sẽ đưa Win Rate quay lại mốc >70%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
