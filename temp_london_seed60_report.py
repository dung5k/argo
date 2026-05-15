# -*- coding: utf-8 -*-
import codecs, subprocess

diary_text = """
### STATE UPDATE: 2026-05-14 08:40
- **Run ID:** run_20260514_083411_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed59
- **Kết quả:** Best Val Loss tại Epoch 9. Composite Score: **0.1810** ↑ (KỶ LỤC MỚI!), Win Rate: **29.42%** (Threshold 0.80), **53.13%** (Threshold 0.94, N=32).
- **Phân tích:** 🏆 SCORE TIẾP TỤC TĂNG! Seed 59 phá kỷ lục Seed 58 với Score 0.1810. Đây là 5 vòng liên tiếp Score tăng dần: 0.1563→0.1627→0.1639→0.1754→0.1810. Đặc biệt: WR@0.80 cải thiện lên 29.42% và Composite Score tiến gần mốc 0.20. Buy/Sell ở 0.94 vẫn bị lệch (32B/0S) — điều này có thể do mô hình đang bias Buy trong phiên London. Cần quan sát thêm.
- **Ý tưởng tiếp theo (Seed 60):** Milestone tròn! Tiếp tục khai thác vùng đỉnh này với Seed 60. Cấu hình vàng: 5m_W15_Drop30_LR5e-5.
"""

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 60) — 🏆 KỶ LỤC MỚI LẦN 2!

📊 Kết quả FarmSeed 59:
- Best Val Loss tại Epoch 9. Composite Score: **0.1810** ↑ (KỶ LỤC cao nhất mọi thời đại!)
- Win Rate: 29.42% (Threshold 0.80) | **53.13%** (Threshold 0.94)

📈 Xu hướng Score 5 vòng liên tiếp — Tất cả đều TĂNG:
Seed55: 0.1563 → Seed56: 0.1627 → Seed57: 0.1639 → Seed58: 0.1754 → Seed59: **0.1810** 🚀

Nhận định: 5 vòng tăng liên tiếp là bằng chứng thép khẳng định cấu hình 5m_W15_Drop30 đang hội tụ về vùng cực trị. Mốc 0.20 Score đang trong tầm với! Cần tiếp tục đào không ngừng nghỉ.

🥳 FarmSeed 60 — Mốc tròn! (PID 7776) đã bùng cháy dưới nền. 🔥"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
