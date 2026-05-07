# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 16:27:00] - Lượt đánh giá Run 125: CHIẾN THẮNG ĐẦU TIÊN (Decisive Sprint)
- **Kết quả Run trước (Run 125):** Composite Score = 0.51, Win Rate = **74.19%** (tại ngưỡng 0.66).
- **Phân tích chuyên gia:** 
    - **CLEAN_DATA_DIET** là bước ngoặt: Việc loại bỏ 80% dữ liệu nhiễu giúp mô hình tập trung hoàn toàn vào các pha bứt phá.
    - Kết quả đạt đỉnh ngay tại Epoch 1, sau đó Overfitting rất nhanh. Điều này chứng tỏ kiến thức về "Cú bứt phá" rất dễ học nhưng tập dữ liệu nhỏ (23k mẫu) dễ khiến mô hình bị học vẹt.
    - WR 74% là mốc cực kỳ hứa hẹn cho phiên Á.
- **Ý tưởng thử nghiệm tiếp theo (Run 126 - Refined Decisive):** 
    - **Giảm FAST_HIT_BARS=5**: Ép AI chỉ học các cú bứt phá "chớp nhoáng" hơn nữa (chạm TP trong vòng 5 phút).
    - **LAYER_DROP=0.2** & **LEARNING_RATE=1e-5**: Tăng cường điều tiết (regularization) và giảm tốc độ học để chống Overfitting sớm.
    - **MTF_WINDOWS=[15, 60]**: Thêm ngữ cảnh xu hướng khung lớn để AI không bị "đánh lừa" bởi các cú bứt phá giả (Fakeout).
- **Giả thuyết (Hypothesis):** Bằng cách kết hợp giữa "Sát thủ chớp nhoáng" (Fast Hit) và "Bức tranh lớn" (MTF), mô hình sẽ đạt được độ ổn định cao hơn, kéo dài thời gian hội tụ và vượt ngưỡng WR 80%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
