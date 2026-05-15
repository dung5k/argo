# -*- coding: utf-8 -*-
import codecs

diary_text = """
### STATE UPDATE: 2026-05-14 08:21
- **Run ID:** run_20260514_081159_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed56
- **Kết quả:** Early Stopping tại Epoch 84. Best Val Loss tại Epoch 6 - Composite Score: **0.1627**, Win Rate: **28.65%** (Threshold 0.80), **46.0%** (Threshold 0.94, N=50).
- **Phân tích:** Seed 56 tiếp tục xác nhận xu hướng tích cực của cấu hình 5m_W15_Drop30. Composite Score tiếp tục được duy trì ở mức 0.1627 (ổn định so với Seed 55: 0.1563). Điểm nổi bật đặc biệt: ở ngưỡng lọc cực cao 0.94, Win Rate đạt **46%** với 50 tín hiệu cân bằng Buy/Sell (28B/22S) — đây là một tỷ lệ cực kỳ ấn tượng cho phiên London. Cấu hình này đang hội tụ dần về một vùng ổn định.
- **Ý tưởng tiếp theo (Seed 57):** Giữ nguyên bộ gen "Vàng Mới": 5m, W15, Drop=0.3, LR=5e-5. Tiếp tục khai thác Stochastic Mining để tìm điểm hội tụ tốt hơn nữa.
"""

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)
print("Diary updated.")
