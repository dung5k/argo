# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 13:57:00] - Lượt đánh giá Run: run_20260504_1327_v4_assassin (Thất bại/Xóa tự động)
- **Kết quả Run trước:** Đã bị hệ thống tự động xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Việc Run 121 (Silent Assassin) vẫn bị xóa chứng tỏ rằng vấn đề không chỉ nằm ở thời gian giữ lệnh. Mô hình dường như đang gặp khó khăn trong việc trích xuất tín hiệu Alpha từ bộ dữ liệu V4 Pro. Sự xuất hiện của `LTCBTC` hoặc các đặc trưng `MTF` có thể đang tạo ra quá nhiều nhiễu trong giai đoạn khởi đầu, khiến Gradient bị chệch hướng hoàn toàn.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Triển khai **Run 122** với cấu hình **"Nguyên bản Baseline" (The Originalist)**.
    2. Loại bỏ hoàn toàn MTF và LTCBTC.
    3. Quay lại danh mục mã dẫn dắt truyền thống của phiên Á: **BTC, ETH, XRP, BCH, DOGE**.
    4. Giữ nguyên **Hold 12m** và **2 Layers** (vì đây là cấu trúc mạnh nhất của Baseline).
    5. Hạ **Window Size về 20** (y hệt Baseline Run 18).
- **Giả thuyết (Hypothesis):** Bằng cách loại bỏ các đặc trưng "thời thượng" nhưng gây nhiễu (MTF, LTCBTC) và quay về đúng công thức đã giúp Run 18 đạt 85%, chúng ta sẽ cung cấp cho AI một lộ trình học tập sạch sẽ nhất. Sự tối giản tuyệt đối này sẽ giúp Win Rate vượt ngưỡng 60% và bắt đầu chu trình tối ưu hóa thực sự.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
