import os
import subprocess

msg = "🚀 [NY Expert] Máy đang bận chạy run_ah. Đã phân tích ý tưởng mới: Bật LẠI ORDER_FLOW kết hợp VOL_REGIME để bắt trọn vi mô/vĩ mô phiên NY. Nhật ký HF đã cập nhật và đưa kịch bản run_20260428_231200_v3_ny_ai vào Hàng đợi chờ!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
