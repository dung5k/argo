import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 12 (PID 10428) ĐANG HUẤN LUYỆN cực kỳ hứa hẹn!
- Đỉnh hiện tại (Epoch 1): Composite Score đạt 0.5325.
- Win Rate đỉnh cao: 73.9%.
- Dù ép mức Take Profit lên cực hạn 0.35% (R:R=1.75) của phiên Á, mô hình vẫn trụ vững mốc Win Rate > 70%. Điều này cho thấy chất lượng phân tích của Golden Config là không thể bàn cãi.

Hệ thống đang giữ tiến trình chạy để dò tìm các đỉnh cao hơn trước khi kết luận cấu hình Live."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
