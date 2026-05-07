import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = """
### [2026-05-03 23:28:00] - Lượt đánh giá Run: run_20260503_230000_v3_asian_auto_94 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Việc quay lại Window 45m vẫn không cứu vãn được tình thế khi kích hoạt Zero Noise Target. Có vẻ như cơ chế Zero Noise đang "lọc quá tay", khiến mô hình bị mất đi các tín hiệu nhỏ nhưng quan trọng trong phiên Á, hoặc nó tạo ra một sự mất cân bằng dữ liệu ngầm mà chúng ta chưa kiểm soát được. Ngoài ra, việc mở rộng BCH có thể đã làm tăng chiều dữ liệu nhiễu vượt quá khả năng xử lý của 1-layer Transformer.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Quay lại cấu hình **Run 92** (Mốc 61% WR) làm nền tảng.
    2. Tắt **ZERO_NOISE_TARGET** (Về False).
    3. Nâng **BATCH_SIZE lên 512** để làm mượt gradient trong môi trường nhiễu.
    4. Kích hoạt **LAYER_DROP = 0.1** để tăng tính tổng quát hóa (Regularization).
- **Giả thuyết (Hypothesis):** Batch Size lớn hơn sẽ giúp mô hình nhìn thấy bức tranh toàn cảnh hơn về phân phối xác suất trong phiên Á, tránh bị "giật" bởi các nhiễu lệnh lẻ tẻ. Layer Drop sẽ giúp kiến trúc Transformer bền bỉ hơn, không bị quá phụ thuộc vào một vài đặc trưng macro cụ thể. Hy vọng sự ổn định này sẽ đẩy Win Rate vượt ngưỡng 70%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
