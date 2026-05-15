import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 32 (PID 10472) đang hoạt động!
- Tình trạng: Lượt chạy Xác Thực (Validation Run) cho biểu đồ 5 phút đang trong giai đoạn nạp dữ liệu và khởi tạo môi trường.
- Hệ thống đang kiểm soát chặt chẽ tiến trình này trong background. Do lượng dữ liệu OrderFlow 5 phút cần được tổng hợp lại từ dữ liệu gốc, quá trình khởi tạo có thể mất vài phút. Kết quả sẽ được báo cáo ngay khi có `training_metrics_v3.json`.

Hệ thống đang nhàn rỗi và sẵn sàng cho các lệnh kế tiếp."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
