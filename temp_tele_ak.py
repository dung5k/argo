import os
import subprocess

msg = "🚀 [NY Expert] Lượt trước (run_aj) không vượt qua 0.60 nên đã tự hủy. Đã phát hiện máy rảnh tay. Tiến hành xuất kích kịch bản mới: Mở rộng WINDOW_SIZE tối đa lên 90 phút để mô hình 'nuốt trọn' bối cảnh Á-Âu trước thềm NY, kết hợp LAYER_DROP 0.1 chống Overfitting. Đang tạo Tensor và Train run_20260429_000500_v3_ny_ak..."

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--done"])
