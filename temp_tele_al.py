import os
import subprocess

msg = "🚀 [NY Expert] Máy đang BẬN cày cấu hình Macro 90 phút (run_ak). Đã phân tích ý tưởng mới: Nâng cấp não bộ bằng cấu trúc Residual Head kết hợp Layer Drop 0.2 để tăng khả năng suy luận sâu. Kịch bản run_20260429_001200_v3_ny_al đã cập nhật HF và đưa vào Hàng đợi chờ!"

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
