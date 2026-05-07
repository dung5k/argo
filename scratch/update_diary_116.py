# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 10:57:00] - Lượt đánh giá Run: run_20260504_102700_v3_asian_auto_115 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Thất bại sớm).
- **Phân tích chuyên gia:** Ngay cả cấu hình "Siêu tối giản" (Window 20) cũng thất bại sớm. Điều này chỉ ra rằng vấn đề không chỉ nằm ở RAM mà có thể là sự xung đột tài nguyên GPU hoặc lỗi khởi tạo môi trường (CUDA/Torch). Khi máy cục bộ đang xử lý nhiều tác vụ đồng thời, bộ nhớ đồ họa có thể bị phân mảnh, khiến việc khởi tạo mô hình Transformer (dù nhỏ) cũng gặp khó khăn.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Lập tức dispatch **Run 116** với cấu hình **"Sống sót tối thượng" (Ultimate Survival)**.
    2. Hạ **Window Size xuống 15** và **loại bỏ hoàn toàn MTF**.
    3. Hạ **D_MODEL xuống 32** và **Batch Size xuống 64**.
    4. Đây là cấu hình thấp nhất có thể để kiểm tra xem script huấn luyện có thể chạy được hay không.
- **Giả thuyết (Hypothesis):** Nếu cấu hình "Sống sót tối thượng" này vẫn thất bại, chúng ta có thể khẳng định máy cục bộ đang gặp lỗi phần cứng/môi trường CUDA và cần khởi động lại hoặc giải phóng GPU thủ công. Nếu nó chạy được, chúng ta sẽ bắt đầu xây dựng lại từ nền tảng cực thấp này để tìm ra ngưỡng giới hạn mới của phiên Á.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
