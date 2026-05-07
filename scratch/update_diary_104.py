# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 04:00:00] - Lượt đánh giá Run: run_20260504_032800_v3_asian_auto_103 (Đang chạy)
- **Kết quả Run trước:** Đang huấn luyện (Batch 64 + Simple Head).
- **Phân tích chuyên gia:** Thành công của Run 102 đã xác định được "bộ khung" chuẩn cho phiên Á: Simple Head + 45m + LTCBTC + Order Flow. Bây giờ là lúc gia cố thêm khả năng phòng ngự của mô hình trước các xu hướng lớn từ phiên Mỹ/London để lại.
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Chuẩn bị **Run 104** với cơ chế **Đa khung thời gian sâu (Deep MTF)**.
    2. Bổ sung khung **240 phút (4 giờ)** vào `MTF_WINDOWS`.
    3. Giữ nguyên kiến trúc Simple Head chiến thắng.
- **Giả thuyết (Hypothesis):** Phiên Á thường là giai đoạn tích lũy sau các đợt sóng lớn của phiên Âu/Mỹ. Việc bổ sung khung 4h sẽ giúp Attention Mechanism nhận diện được "vùng giá trị" dài hạn, tránh việc AI phát tín hiệu mua/bán ngược lại với xu hướng chủ đạo của ngày hôm đó. Sự tham chiếu này hy vọng sẽ nâng cao Sharpe Ratio và đưa Win Rate ổn định trên mức 80%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
