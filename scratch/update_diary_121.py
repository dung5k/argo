# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 13:27:00] - Lượt đánh giá Run: run_20260504_1257_v4_patience (Thất bại/Xóa tự động)
- **Kết quả Run trước:** Đã bị hệ thống tự động xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Việc tăng thời gian giữ lệnh (Hold 60m) không cứu được mô hình, thậm chí có thể làm tệ hơn. Nhìn lại Baseline Run 18 (85% WR), chúng ta thấy nó chỉ giữ lệnh trong **12 phút**. Điều này cho thấy phiên Á có đặc thù là các "xung lực" (impulses) cực ngắn. Việc giữ lệnh quá lâu chỉ làm tăng khả năng bị quét Stop Loss bởi nhiễu ngẫu nhiên.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Triển khai **Run 121** theo phong cách **"Sát thủ thầm lặng" (The Silent Assassin)**.
    2. Quay lại **MAX_HOLD_BARS = 12** (Đánh nhanh rút gọn).
    3. Sử dụng **Batch Size 256** (để mô hình học được phân phối dữ liệu rộng hơn trong mỗi bước).
    4. Cấu trúc **2 Layer Transformer** (nhằm bắt được các mối quan hệ phi tuyến tính phức tạp hơn mà 1 lớp không làm được).
    5. Giữ **Window Size ở mức 25** để cân bằng giữa bối cảnh và tài nguyên.
- **Giả thuyết (Hypothesis):** Sự kết hợp giữa việc đánh ngắn (12m) và độ sâu kiến trúc (2 Layers) sẽ giúp AI nhận diện được các nhịp "Scale-in/Scale-out" của dòng tiền phiên Á. Batch 256 sẽ cung cấp sự ổn định cần thiết để Win Rate vượt qua mốc 60% và bứt phá lên các tầm cao mới.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
