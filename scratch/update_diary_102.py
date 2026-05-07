# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 02:58:00] - Lượt đánh giá Run: run_20260504_020000_v3_asian_auto_100 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Chiến thuật Scalping 15 phút đã thất bại hoàn toàn. Điều này cho thấy trong phiên Á, các dao động ngắn hạn mang tính ngẫu nhiên quá cao, không có cấu hình Alpha bền vững để AI khai thác. Mọi nỗ lực "ép" mô hình nhìn ngắn hạn đều dẫn đến việc học phải nhiễu.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Lập tức dispatch **Run 101** (45m + LTCBTC + Order Flow) để kiểm chứng giả thuyết "Toàn diện Alpha".
    2. Chuẩn bị **Run 102** với chiến thuật **"Tối giản Phân loại"**.
    3. Quay lại **CLS_HEAD = simple** (Thay vì Residual) để giảm bớt sự phức tạp ở đầu ra, tránh việc mô hình "suy diễn" quá đà từ các đặc trưng Price Action + Order Flow.
    4. Giữ nguyên: 45m, LTCBTC, Order Flow, Vol Regime.
- **Giả thuyết (Hypothesis):** Có thể cơ chế Residual CLS_HEAD đang quá mạnh mẽ, khiến mô hình cố gắng ghi nhớ (overfit) các mẫu hình Price+Order Flow đặc thù của tập train phiên Á. Việc quay lại Simple Head sẽ buộc mô hình phải dựa vào các đặc trưng tổng quát hơn từ Transformer block, giúp tăng tính bền bỉ (robustness) khi đối mặt với dữ liệu validation.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
