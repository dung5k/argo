import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 21 (PID 8792) đang hoạt động!
- Tình trạng: Mô hình đang trong giai đoạn khởi tạo môi trường và xử lý (extract) dataset cho lượt "Validation Run" (Xác thực lại Golden Config).
- Hệ thống đang kiểm soát chặt chẽ tiến trình này trong background. Các chỉ số hiệu suất đầu tiên sẽ được phân tích và báo cáo ngay khi Epoch 1 hoàn tất.

Hệ thống nhàn rỗi và sẵn sàng cho các chỉ thị tiếp theo."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
