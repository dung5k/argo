# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 02:00:00] - Lượt đánh giá Run: run_20260504_012800_v3_asian_auto_99 (Đang chạy)
- **Kết quả Run trước:** Đang huấn luyện (Epoch 1).
- **Phân tích chuyên gia:** Việc đưa LTCBTC vào là một bước đi đúng đắn để định vị tương quan. Tuy nhiên, nếu Window 45m vẫn tỏ ra quá chậm chạp trong việc bắt các "con sóng lăn tăn" của phiên Á, chúng ta cần một phương án dự phòng mang tính bứt phá về tần suất.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Triển khai **Run 100** với chiến thuật **Scalping siêu tốc**.
    2. Hạ **WINDOW_SIZE xuống 15 phút**.
    3. Hạ **TP_PCT / SL_PCT xuống 0.2%**.
    4. Giữ nguyên: LTCBTC, Residual Head, D_MODEL 64.
- **Giả thuyết (Hypothesis):** Một góc nhìn siêu ngắn hạn (15 phút) có thể bắt được các nhịp dao động li ti của phiên Á mà cửa sổ 45 phút thường bỏ qua hoặc coi là nhiễu. Với mức TP 0.2%, chúng ta chỉ cần một cú hích nhẹ từ dòng tiền để chốt lời. Đây là chiến thuật "tích tiểu thành đại" để vượt qua sự ảm đạm của phiên Á.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
