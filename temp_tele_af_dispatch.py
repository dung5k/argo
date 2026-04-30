import os
import subprocess

msg = "🚀 [NY Expert] Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản dự phòng từ Hàng đợi: Bật VOL_REGIME và LAYER_DROP 0.2 để giảm thiểu phụ thuộc cục bộ. Đang train run_20260428_213500_v3_ny_af..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
