# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 09:57:00] - Lượt đánh giá Run: run_20260504_075800_v3_asian_auto_112 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Thất bại sớm/OOM).
- **Phân tích chuyên gia:** Run 112 (Batch 256) đã biến mất khỏi hệ thống chỉ sau chưa đầy 30 phút. Nhiều khả năng việc tăng Batch Size lên 256 kết hợp với Window 45 đã gây ra lỗi tràn bộ nhớ GPU (OOM) trong quá trình huấn luyện, khiến tiến trình bị kill ngay lập tức. Điều này cho thấy tài nguyên phần cứng cục bộ có giới hạn nghiêm ngặt, chúng ta không thể "vỗ béo" Batch Size quá mức.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Lập tức dispatch **Run 113** (Mean Pooling + Window 35) để kiểm chứng khả năng ổn định bằng cách "nhìn bao quát".
    2. Chuẩn bị **Run 114** với chiến thuật **"Bối cảnh đa tầng" (Triple MTF Context)**.
    3. Quay lại **Window 30** (để dành tài nguyên cho MTF).
    4. Kích hoạt 3 tầng MTF: **[5m, 15m, 60m]**.
- **Giả thuyết (Hypothesis):** Nếu "Cái nhìn điềm tĩnh" (Mean Pooling) là đúng, thì việc bổ sung thêm bối cảnh đa tầng (5m cho ngắn hạn, 15m cho trung hạn và 60m cho xu hướng dài hạn của phiên) sẽ giúp mô hình 1 lớp Transformer có đủ thông tin để ra quyết định mà không cần kiến trúc sâu. Việc sử dụng Window 30 giúp mô hình chạy mượt mà trên GPU mà không lo OOM.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
