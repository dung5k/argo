import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 40 (PID 8728) đang rực lửa!
- Tình trạng: Lượt Đào Vàng Holy Grail Lần 6 đang trong những Epoch đầu tiên, khởi tạo ma trận trọng số. 
- Mọi tài nguyên CPU/GPU đã được tối ưu hóa. Lưới lọc Auto-Tuning đang trực chiến để chặn bắt bất kỳ cấu hình lỗi nào.

Hệ thống đang kiểm soát chặt chẽ toàn cục và chờ ở trạng thái nhàn rỗi."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
