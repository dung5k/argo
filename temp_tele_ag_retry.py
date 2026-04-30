import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_ag) bị crash đột ngột (khả năng cao do thiếu RAM khi Train). Máy hiện tại đã IDLE. Tiến hành xuất kích lại kịch bản dự phòng từ Hàng đợi: Giảm LEARNING_RATE xuống 5e-5 và POOLING attention. Đang train lại run_20260428_220500_v3_ny_ag..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
