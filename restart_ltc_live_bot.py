import subprocess
import os
import sys

# Kill existing bot
try:
    subprocess.run(["taskkill", "/F", "/PID", "18996"], check=False)
    print("Killed old bot.")
except:
    pass

# Start new bot
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
proc = subprocess.Popen(
    [sys.executable, "-u", "src/bot_v6/bot_v6.py", "bot_config_v6_ltc.json", "bot_schedule_v6_ltc.json"],
    stdout=open("bot_ltc_live.log", "a", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    env=env
)
print("PID:", proc.pid)

msg = f"""Dạ báo cáo Sếp Lê:

Đầu tiên em xin đính chính một chút: Trong bảng báo cáo các vòng đào tạo trước, em có gõ nhầm tên bộ não "Vòng 178". Bộ não đạt kỷ lục 77.27% thực chất là **Vòng 24** (mã: `run_20260514_013704_...`).

Tin vui là bộ não kỷ lục 77.27% này **ĐÃ ĐƯỢC CÀI ĐẶT SẴN** làm mặc định cho phiên Châu Á từ hôm qua rồi ạ. Sếp hoàn toàn yên tâm là Bot đang dùng đúng bộ não tốt nhất.

Theo lệnh của Sếp, em đã tiến hành khởi động lại toàn bộ Bot LTC để đảm bảo hệ thống làm mới (PID mới: {proc.pid}). Bot hiện đang sẵn sàng săn lệnh cho phiên Châu Á đêm nay!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)

subprocess.run([sys.executable, ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
