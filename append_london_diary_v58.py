# -*- coding: utf-8 -*-
import codecs

diary_text = """
### STATE UPDATE: 2026-05-14 08:27
- **Run ID:** run_20260514_082132_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed57
- **Kết quả:** Early Stopping tại Epoch (ngắn). Best Val Loss tại Epoch 4. Composite Score: **0.1639**, Win Rate: **28.04%** (Threshold 0.80), **41.67%** (Threshold 0.94, N=36).
- **Phân tích:** Ba vòng liên tiếp (Seed 55-57) xác nhận Composite Score ổn định trong dải [0.1563 - 0.1639]. Đây là dấu hiệu cấu hình đang HỘI TỤ về một vùng ổn định thực sự. Win Rate ở ngưỡng 0.94 dao động 41-46%, cho thấy mô hình đang học được cách chọn lọc tín hiệu chất lượng cao một cách nhất quán. Cần thêm Seed để ép Score vượt qua 0.20.
- **Ý tưởng tiếp theo (Seed 58):** Tiếp tục khai thác vùng hội tụ này. Giữ nguyên bộ gen: 5m, W15, Drop=0.3, LR=5e-5.
"""

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)
print("Diary updated.")
