import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (Tắt Order Flow + Attention) thất bại do điểm nhỏ hơn 0.60. Ý tưởng mới: Mở rộng WINDOW_SIZE lên 60 phút để nhìn xu hướng gốc, giữ nguyên các tính năng trước đó. Đang train run_20260428_210000_v3_ny_ae..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
