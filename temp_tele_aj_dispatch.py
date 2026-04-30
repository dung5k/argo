import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_ai) không vượt qua mốc 0.60 nên đã tự dọn dẹp. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản dự phòng từ Hàng đợi: Bật Multi-Timeframe (15 phút + 60 phút) kết hợp Attention Pooling để chắt lọc tín hiệu chống Fakeout đầu phiên. Đang train run_20260428_234200_v3_ny_aj..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
