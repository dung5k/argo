import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 25 (PID 1588) đang hoạt động!
- Tình trạng: Lượt chạy Xác Thực (Validation Run) của Tân Vương Golden Config (Vòng 24) đang trong giai đoạn nạp dữ liệu và khởi tạo môi trường huấn luyện.
- Hệ thống đang kiểm soát chặt chẽ quá trình này trong background. Các chỉ số xác thực sẽ được hệ thống phân tích và báo cáo ngay khi có kết quả.

Hệ thống đang nhàn rỗi và sẵn sàng cho các lệnh kế tiếp."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
