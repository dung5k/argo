import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_ag) thất bại do điểm số không đạt yêu cầu. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản mới: Thu hẹp WINDOW_SIZE xuống 15 phút kết hợp POOLING attention để bắt nhịp sóng siêu ngắn đầu phiên (Scalping). Đang train run_20260428_231000_v3_ny_ah..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
