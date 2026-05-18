import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ - Vòng 194 (HolyGrail_Replication_194) đang tải dữ liệu Tensors từ HuggingFace (Chưa bắt đầu Epoch 1). Hệ thống sẽ báo cáo kết quả ở chu kỳ tiếp theo!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)

subprocess.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
