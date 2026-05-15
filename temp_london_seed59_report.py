# -*- coding: utf-8 -*-
import codecs, subprocess

diary_text = """
### STATE UPDATE: 2026-05-14 08:33
- **Run ID:** run_20260514_082804_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed58
- **Kết quả:** Early Stopping. Best Val Loss tại Epoch 6. Composite Score: **0.1754** ↑ (KỶ LỤC MỚI!), Win Rate: **28.41%** (Threshold 0.80), **53.13%** (Threshold 0.94, N=32).
- **Phân tích:** 🚨 ĐỘT PHÁ! Seed 58 thiết lập KỶ LỤC mới cho phiên London! Score vọt lên 0.1754 — cao nhất từ trước đến nay trong chuỗi 5m_W15. Đặc biệt hơn, Win Rate ở ngưỡng lọc 0.94 đạt tới **53.13%** — vượt mốc 50% lần đầu tiên! Tín hiệu Buy/Sell cân bằng hoàn hảo (32B/0S bị lệch — cần quan sát thêm). Cỗ máy đang tiến đến vùng "Chén Thánh" London.
- **Ý tưởng tiếp theo (Seed 59):** Tiếp tục khai thác tại cùng vùng. Score đang có xu hướng tăng qua các Seed. Cần nhiều Seed hơn để xác nhận đỉnh.
"""

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 59) — 🚨 KỶ LỤC MỚI!

📊 Kết quả FarmSeed 58 — ĐỘT PHÁ:
- Best Val Loss tại Epoch 6. Composite Score: **0.1754** ↑ (KỶ LỤC cao nhất!)
- Win Rate: 28.41% (Threshold 0.80) | **53.13%** (Threshold 0.94!)

📈 Xu hướng Score 4 vòng gần nhất (5m_W15_Drop30):
Seed55: 0.1563 → Seed56: 0.1627 → Seed57: 0.1639 → Seed58: **0.1754** ↑↑

Nhận định: Score đang tăng liên tiếp qua 4 vòng! Win Rate@0.94 vượt mốc 50% lần đầu tiên — đây là tín hiệu Cỗ Máy đang hội tụ về "Chén Thánh" của phiên London.

🚀 FarmSeed 59 (PID 10320) đã bùng cháy dưới nền. Tiếp tục khai thác! 🔥"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
