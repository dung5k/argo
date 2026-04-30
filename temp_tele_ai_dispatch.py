import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_ah) chưa đủ điểm qua 0.60 nên đã tự hủy. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản dự phòng từ Hàng đợi: Bật LẠI ORDER_FLOW kết hợp VOL_REGIME để theo dõi cả vi mô và vĩ mô phiên NY. Đang train run_20260428_231200_v3_ny_ai..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
