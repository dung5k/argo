# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 16:57:00] - Lượt đánh giá Run 126: SỰ THẬN TRỌNG ĐÁNH MẤT CƠ HỘI
- **Kết quả Run trước (Run 126 - Refined Decisive):** Composite Score = 0.37, Win Rate = 62.5% (tại ngưỡng 0.63). Mô hình đạt đỉnh ở Epoch 63.
- **Phân tích chuyên gia:** 
    - Việc giảm `LEARNING_RATE=1e-5` và thêm `LAYER_DROP=0.2` đã thành công trong việc ngăn chặn Overfitting (chạy được tới Epoch 63 thay vì dừng ở Epoch 1 như Run 125).
    - TUY NHIÊN, Win Rate đã sụt giảm từ 74% xuống 62.5%. 
    - Nguyên nhân chính: Việc ép `FAST_HIT_BARS=5` quá gắt đã làm mất đi nhiều mẫu dữ liệu tốt. Hơn nữa, việc thêm `MTF_WINDOWS=[15, 60]` tạo ra sự "mâu thuẫn" trong tín hiệu: Mô hình bị ngần ngại không dám bắt các nhịp bứt phá ngắn hạn nếu xu hướng dài hạn (60m) đang ngược chiều.
- **Ý tưởng thử nghiệm tiếp theo (Run 127 - The Balanced Sprinter):** 
    - **Nới lỏng FAST_HIT_BARS=8**: Quay lại cấu hình lọc dữ liệu thành công của Run 125.
    - **Loại bỏ MTF_WINDOWS**: Tập trung hoàn toàn vào vi cấu trúc ngắn hạn (`WINDOW_SIZE=30`), bỏ qua xu hướng dài hạn để mô hình tự tin bắt sóng nhỏ.
    - **Chuyển POOLING sang "mean"**: Attention Pooling dễ bị overfit vào các cây nến nhiễu (spikes). Mean Pooling sẽ tạo ra Embedding ổn định hơn trên tập dữ liệu nhỏ.
    - Giữ nguyên "Giáp chống overfit": `LAYER_DROP=0.2`, `LEARNING_RATE=1e-5`, `BATCH_SIZE=128`.
- **Giả thuyết (Hypothesis):** Bằng cách trả lại môi trường dữ liệu đã giúp Run 125 đạt WR 74%, nhưng áp dụng thêm cơ chế chống Overfit và Mean Pooling, mô hình sẽ hội tụ từ từ và ổn định ở mức WR > 70% mà không bị xẹp xuống nhanh chóng.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
