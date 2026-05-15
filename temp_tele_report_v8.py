import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 8).
📊 Kết quả Vòng 7: THÀNH CÔNG RỰC RỠ! 
- Đạt Composite Score: 0.5184
- Win Rate: 68.89% (Đỉnh mới, tăng mạnh từ 63.04%)
- Dừng sớm tại Epoch 55.

🚀 Triển khai Vòng 8:
1. Tiếp đà chiến thắng, ép Dropout lên 0.25 và siết Learning Rate xuống 2e-5.
2. Mục tiêu: Vắt kiệt sức mạnh của mô hình, loại bỏ hoàn toàn các false signals để đánh bục mốc Win Rate 70%.
3. Tiến trình Vòng 8 (PID 12028) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
