import os
import subprocess

msg = "🚀 [NY Expert] Máy đang bận chạy run_ai. Đã phân tích ý tưởng mới: Bật Multi-Timeframe (15 phút + 60 phút) để so sánh chéo, chống nhiễu Fakeout đầu phiên NY. Kịch bản run_20260428_234200_v3_ny_aj đã cập nhật HF và đưa vào Hàng đợi chờ!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
