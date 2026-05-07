# -*- coding: utf-8 -*-
import os

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V3_5\ASIAN_TRAINING_DIARY.md'
new_entry = u"""
### [2026-05-04 01:28:00] - Lượt đánh giá Run: run_20260504_005800_v3_asian_auto_98 (Thất bại)
- **Kết quả Run trước:** Đã bị hệ thống xóa (Win Rate < 60%).
- **Phân tích chuyên gia:** Ngay cả khi quay lại Baseline kỷ lục Run 77, mô hình vẫn không thể vượt qua ngưỡng 60%. Điều này xác nhận một sự thật phũ phàng: Chế độ thị trường (Market Regime) của phiên Á đã thay đổi so với 2 ngày trước. Việc loại bỏ Order Flow là đúng đắn để giảm nhiễu, nhưng chúng ta đang thiếu một "kim chỉ nam" về dòng tiền thông minh luân chuyển giữa các hệ sinh thái (Rotation).
- **Ý tưởng thử nghiệm tiếp theo:** 
    1. Tiếp tục giữ cấu hình "sạch" (Window 45, No Order Flow).
    2. Bổ sung **ETHBTC** vào danh mục Macro Features. 
    3. Nâng **LEARNING_RATE lên 5e-5** để mô hình thích nghi nhanh hơn với các biến động mới nhất.
- **Giả thuyết (Hypothesis):** Tỷ giá ETH/BTC là chỉ báo quan trọng nhất về khẩu vị rủi ro (Risk-on/Risk-off) trong thị trường Crypto. Việc bổ sung đặc trưng này sẽ giúp AI nhận diện được khi nào dòng tiền đang đổ vào Altcoin (LTC) và khi nào nó đang rút về BTC. Tốc độ học nhanh hơn sẽ giúp trọng số mô hình bắt kịp với nhịp độ hiện tại của phiên Á. Hy vọng sự nhạy bén này sẽ đẩy Win Rate quay lại mốc 70%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(new_entry)
print("Diary updated successfully.")
