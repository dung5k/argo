# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 14:57:00] - Lượt đánh giá Run: run_20260504_1427_v4_heavy (Thất bại/Xóa tự động)
- **Kết quả Run trước:** Đã bị hệ thống tự động xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Chuỗi thất bại liên tục (116-123) chỉ ra một vấn đề mang tính hệ thống. Việc nới lỏng biên độ lên 0.5% vẫn không đủ để AI vượt qua ngưỡng 60%. Điều này có nghĩa là mô hình đang bị "loạn" tín hiệu hoặc các nhãn (labels) đang quá mất cân bằng trong dữ liệu mới từ Binance. Tôi cần phải quan sát được kết quả thực tế thay vì để hệ thống tự xóa.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Triển khai **Run 124** với tên gọi **"Quan sát viên" (The Observer)**.
    2. **QUYẾT ĐỊNH TỐI THƯỢNG:** Tạm thời vô hiệu hóa cơ chế tự động xóa thư mục Run rác trong code huấn luyện để giữ lại dữ liệu phân tích.
    3. Nới rộng biên độ lên mức tối đa: **SL/TP 1.0% / 1.0%**.
    4. Kéo dài thời gian giữ lệnh lên **30 phút** để AI có đủ không gian quan sát xu hướng lớn hơn.
    5. Quay lại cấu trúc tối giản **D_MODEL 32** để loại trừ khả năng quá tải GPU.
- **Giả thuyết (Hypothesis):** Bằng cách giữ lại thư mục Run (dù Win Rate thấp), tôi sẽ có thể đọc được file log và biểu đồ loss để biết AI đang gặp khó khăn ở đâu (Overfitting hay Underfitting). Biên độ 1.0% sẽ là "phòng thí nghiệm" cuối cùng để tìm ra điểm hội tụ của phiên Á.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
