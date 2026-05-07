import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = """
### [2026-05-03 23:57:00] - Lượt đánh giá Run: run_20260503_232800_v3_asian_auto_95 (Mất tích/Lỗi hệ thống)
- **Kết quả Run trước:** Thư mục Run bị mất tích hoặc lỗi khởi động.
- **Phân tích chuyên gia:** Có vẻ như quá trình khởi tạo Run 95 gặp lỗi hệ thống hoặc bị xung đột phần mềm dọn dẹp. Tuy nhiên, chiến thuật "Ổn định Gradient" vẫn là hướng đi đúng đắn nhất hiện tại sau thất bại của Zero Noise.
- **Ý tưởng thử nghiệm tiếp theo:** Tái triển khai chiến thuật của Run 95 vào **Run 96**: Batch Size 512, Layer Drop 0.1, tắt Zero Noise, quay lại Baseline Run 92.
- **Giả thuyết (Hypothesis):** Tương tự Run 95. Hy vọng lần này việc triển khai sẽ thông suốt và mang lại kết quả ổn định.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
