import os
import subprocess

msg = "🚀 [NY Expert] Máy đang bận chạy run_af. Đã nảy ra ý tưởng dự phòng mới: Giảm LEARNING_RATE xuống 5e-5 kết hợp POOLING attention để học chậm lại và tránh nhiễu. Đã đưa run_ag vào Hàng đợi chờ. Nhật ký HF đã cập nhật!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
