import os
import subprocess

msg = "🚀 [NY Expert] Cảnh báo: Lượt trước (run_ak) đã bị Crash (OOM) do đẩy Window Size lên quá cao (90). Tôi đã dọn dẹp xác file thừa để giải phóng bộ nhớ. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản dự phòng từ Hàng đợi: Nâng cấp não bộ bằng cấu trúc Residual Head kết hợp Layer Drop 0.2 để tăng khả năng suy luận sâu. Đang train run_20260429_001200_v3_ny_al..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
