import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 37 (PID 11216) đang hoạt động!
- Tình trạng: Lượt Đào Vàng Holy Grail Lần 3 đang trong giai đoạn khởi tạo và sinh số ngẫu nhiên ban đầu. 
- Mọi tài nguyên CPU/GPU đã được khóa an toàn để tránh quá tải RAM. Kết quả đào vàng sẽ được báo cáo tự động khi kết thúc tiến trình.

Hệ thống đang kiểm soát chặt chẽ toàn cục và chờ ở trạng thái nhàn rỗi."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
