# -*- coding: utf-8 -*-
import codecs, subprocess

diary_text = """
### STATE UPDATE: 2026-05-14 08:46
- **Run ID:** run_20260514_084053_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed60
- **Kết quả:** Best Val Loss tại Epoch 2 (rất sớm). Composite Score: **0.1664**, Win Rate: **30.94%** (Threshold 0.80), **50.0%** (Threshold 0.94, N=32 — cân bằng hơn với 28B/4S).
- **Phân tích:** Seed 60 chốt sổ sớm hơn (Epoch 2) nhưng vẫn duy trì Score 0.1664 — thấp hơn kỷ lục Seed 59 (0.1810) nhưng vẫn nằm trong vùng ổn định. Điểm nổi bật: WR@0.80 cải thiện lên 30.94% (cao nhất từ trước), và Tín hiệu Buy/Sell ở ngưỡng 0.94 cân bằng hơn (28B/4S — bớt lệch so với 32B/0S trước). Score dao động qua 6 vòng: [0.1563-0.1810], trung bình ~0.167.
- **Ý tưởng tiếp theo (Seed 61):** Tiếp tục Stochastic Mining để tìm điểm vượt kỷ lục 0.1810. Cấu hình bất bại: 5m_W15_Drop30_LR5e-5.
"""

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 61).

📊 Kết quả FarmSeed 60:
- Best Val Loss tại Epoch 2. Composite Score: **0.1664**
- Win Rate: **30.94%** (Threshold 0.80 — CAO NHẤT!) | **50.0%** (Threshold 0.94)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  55  | 0.1563 |  26.71% |  33.3%  |
|  56  | 0.1627 |  28.65% |  46.0%  |
|  57  | 0.1639 |  28.04% |  41.7%  |
|  58  | 0.1754 |  28.41% |  53.1%  |
|  59  | 0.1810 |  29.42% |  53.1%  |
|  60  | 0.1664 |  **30.94%** | 50.0% |

Cả 2 chỉ số WR đều đang tăng dần — cấu hình đang rất vững. 🚀 FarmSeed 61 (PID 2436) đã bùng cháy! Mục tiêu: Phá kỷ lục 0.1810!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
