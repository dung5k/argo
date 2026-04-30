import os
import subprocess

msg = "🚀 [NY Expert] Máy đang bận chạy run_ae. Đã nảy ra ý tưởng dự phòng: Bật VOL_REGIME và LAYER_DROP 0.2 để giảm thiểu phụ thuộc cục bộ. Đã đưa run_af vào hàng đợi Tensor. Nhật ký HF đã cập nhật!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
