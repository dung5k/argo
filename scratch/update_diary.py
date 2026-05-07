import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = """
### [2026-05-03 23:00:00] - Lượt đánh giá Run: run_20260503_222800_v3_asian_auto_93 (Thất bại thảm hại)
- **Kết quả Run trước:** Win Rate = 24.55% (Đã bị hệ thống xóa).
- **Phân tích chuyên gia:** Một kết quả cực kỳ tệ hại. Việc rút ngắn Window xuống 30m kết hợp với Zero Noise Target dường như đã làm mô hình hoàn toàn mất phương hướng trong phiên Á. Có thể cửa sổ 30 phút là quá ngắn để Zero Noise Target nhận diện được xu hướng bền vững, dẫn đến việc nhãn bị nhiễu hóa nặng nề. Ngoài ra, việc hạ TP/SL xuống 0.25% có thể khiến mô hình bị dính Stop Loss quá sớm trước khi xung lực hình thành.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Quay lại **WINDOW_SIZE = 45 phút** (Mốc ổn định nhất).
    2. Giữ nguyên **TP_PCT / SL_PCT = 0.3%**. 
    3. Giữ nguyên **ZERO_NOISE_TARGET = true** để tiếp tục thử nghiệm khả năng lọc nhiễu trên cửa sổ rộng hơn.
    4. **Mở rộng Mã đầu vào**: Thay vì loại bỏ DOGE, tôi sẽ thử nghiệm thêm **BCH/USDT** với đầy đủ tính năng (log_ret, bb_width, volume, corr_60) vì BCH thường có tương quan cực cao với LTC.
- **Giả thuyết (Hypothesis):** Cửa sổ 45 phút sẽ cung cấp đủ ngữ cảnh để Zero Noise Target hoạt động chính xác. Việc bổ sung BCH với đầy đủ "vũ khí" sẽ tăng cường tín hiệu xác nhận cho LTC, giúp mô hình bứt phá Win Rate trở lại ngưỡng trên 60%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
