import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_af) thất bại do điểm chưa qua 0.60. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản dự phòng từ Hàng đợi: Giảm LEARNING_RATE xuống 5e-5 và bật POOLING attention. Đang train run_20260428_220500_v3_ny_ag..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
