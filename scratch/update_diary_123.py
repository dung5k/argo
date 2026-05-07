# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 14:27:00] - Lượt đánh giá Run: run_20260504_1357_v4_originalist (Thất bại/Xóa tự động)
- **Kết quả Run trước:** Đã bị hệ thống tự động xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Việc ngay cả một bản sao gần như hoàn hảo của Baseline (Run 122) cũng thất bại cho thấy sự thay đổi về động lực thị trường hiện tại. SL/TP 0.3% có vẻ đang bị quét quá dễ dàng bởi độ nhiễu của sàn Binance so với dữ liệu lịch sử trước đây. Chúng ta cần một "Bộ đệm" (Buffer) dày hơn để AI có thể sống sót qua các cú giật nến (wick).
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Triển khai **Run 123** với chiến thuật **"Giáp dày - Tâm tĩnh" (Heavy Armor)**.
    2. Nới rộng **SL/TP lên 0.5%** (thay vì 0.3%) để AI không bị "chết yểu" bởi nhiễu 1-2 phút.
    3. Kích hoạt **`ZERO_NOISE_TARGET: true`** để bỏ qua các tín hiệu mập mờ, chỉ tập trung vào các chuyển động có ý nghĩa.
    4. Tăng nhẹ **Hold Bars lên 15** và **D_MODEL lên 64** để tăng năng lực suy luận.
- **Giả thuyết (Hypothesis):** Bằng cách nới lỏng biên độ (SL/TP 0.5%) và lọc nhiễu ngay từ nhãn dữ liệu (Zero Noise), chúng ta sẽ tạo ra một môi trường "dễ thở" hơn cho AI. Điều này sẽ giúp Win Rate ổn định trên 60% ngay từ đầu, cho phép mô hình tích lũy tri thức và bứt phá về lâu dài.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
