# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 09:34:00] - Lượt đánh giá Run: run_20260504_072800_v3_asian_auto_111 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Thất bại của Run 111 (Zero Noise) cho thấy việc lọc bỏ hoàn toàn các nến sideway (noise) không mang lại sự minh mẫn cho AI phiên Á. Ngược lại, nó có thể đã làm mất đi tính liên tục của dữ liệu, khiến mô hình không hiểu được bối cảnh "chờ đợi" trước khi có một biến động thật sự. Phiên Á là phiên của sự tích lũy, nên việc AI phải học cả cách "nhìn" sideway là điều bắt buộc để phân biệt với đột phá (breakout).
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Lập tức dispatch **Run 112** (Batch 256 + Baseline) để kiểm chứng giả thuyết về sự ổn định Gradient.
    2. Chuẩn bị **Run 113** với chiến thuật **"Gom nhóm Đặc trưng" (Feature Averaging)**.
    3. Quay lại **Baseline Run 102** (1 Layer, D_MODEL 64, Window 45m).
    4. Thay đổi `POOLING` từ "attention" sang **"mean"**.
- **Giả thuyết (Hypothesis):** Attention Pooling đôi khi quá nhạy bén, dẫn đến việc tập trung quá mức vào một vài nến "đột biến nhiễu" của phiên Á. Việc chuyển sang Mean Pooling (trung bình cộng) sẽ buộc mô hình phải nhìn vào giá trị trung bình của cả cửa sổ 45 phút, mang lại cái nhìn bao quát và điềm tĩnh hơn. Sự kết hợp giữa "Cái nhìn điềm tĩnh" và "Đầu ra tối giản" hy vọng sẽ giúp Win Rate bứt phá lên ngưỡng 85%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
