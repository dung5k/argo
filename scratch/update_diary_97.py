import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = """
### [2026-05-04 00:28:00] - Lượt đánh giá Run: run_20260503_235700_v3_asian_auto_96 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Việc tăng Batch Size lên 512 và kích hoạt Layer Drop 0.1 vẫn không giúp mô hình vượt qua được ngưỡng 60%. Có vẻ như trong phiên Á, sự phức tạp của mô hình (D_MODEL=64, 4 heads) đang phản tác dụng, khiến nó cố gắng giải thích các nhiễu ngẫu nhiên của thị trường đi ngang thay vì bỏ qua chúng. Chúng ta cần một kiến trúc "khắc khổ" hơn, tinh gọn hơn để chỉ bắt lấy những tín hiệu Alpha cốt lõi nhất.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Quay lại cấu hình **Run 92** (Mốc 61% WR) nhưng tinh giản kiến trúc.
    2. Hạ **D_MODEL xuống 32** (Slim Model).
    3. Hạ **N_HEAD xuống 2**.
    4. Giữ nguyên **Order Flow** và **Window 45m**.
- **Giả thuyết (Hypothesis):** Một mô hình có dung lượng thấp hơn (D_MODEL=32) sẽ bị ép buộc phải "chắt lọc" thông tin, chỉ giữ lại những đặc trưng có trọng số cao nhất. Điều này hoạt động như một bộ lọc nhiễu tự nhiên, giúp mô hình bám sát các driver thực sự của thị trường thay vì bị sa lầy vào các biến động li ti. Hy vọng sự tinh gọn này sẽ giúp Win Rate bứt phá bền vững trên 70%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
