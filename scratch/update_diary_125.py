# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 15:57:00] - Lượt đánh giá Run 124: THẤT BẠI CỰC ĐOAN (Anti-Alpha)
- **Kết quả Run trước (Run 124):** Composite Score = 0.02, Win Rate = 2.6% - 15%.
- **Phân tích chuyên gia:** 
    - Mô hình bị hiện tượng "Nghịch đảo Alpha" (Anti-Alpha): Win Rate thấp hơn cả ngẫu nhiên (chỉ đạt ~3-6% trên tập Val). 
    - Nguyên nhân có thể do cấu hình SL/TP quá rộng (1.0%) trong khi phiên Á dao động hẹp, dẫn đến việc mô hình bị "lạc lối" giữa hàng chục nghìn nến nhiễu. 
    - Phân bố nhãn cho thấy 71% dữ liệu là Sideway (Class 2), khiến mô hình bị Bias nặng nề.
- **Ý tưởng thử nghiệm tiếp theo (Run 125 - Decisive):** 
    - Kích hoạt **CLEAN_DATA_DIET**: Chỉ giữ lại các mẫu dữ liệu chạm TP/SL trong vòng 8 nến (`FAST_HIT_BARS=8`). Loại bỏ các nến đi ngang kéo dài để ép AI học cách nhận diện "Cú bứt phá".
    - Tăng **D_MODEL=64**: Cung cấp thêm dung lượng não để xử lý các đặc trưng Macro.
    - Bật **ZERO_NOISE_TARGET**: Loại bỏ TA rác của LTC, chỉ tập trung vào log_ret và các biến số vĩ mô từ BTC, ETH.
    - Đưa SL/TP về **0.3%**: Phù hợp với đặc tính dao động của phiên Á.
- **Giả thuyết (Hypothesis):** Bằng cách "ăn kiêng dữ liệu" (Clean Diet), AI sẽ không còn bị phân tâm bởi các giai đoạn đi ngang chiếm 70% thời gian, từ đó tăng khả năng nhận diện các điểm đảo chiều hoặc bứt phá ngắn hạn với độ chính xác cao hơn.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
