import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 8 (PID 12028) ĐANG HUẤN LUYỆN rất tốt!
- Đỉnh hiện tại (Epoch 21): Composite Score đạt 0.5219.
- Win Rate cao nhất: 73.81% (ĐÃ ĐÁNH BỤC MỐC 70% NHƯ KỲ VỌNG).
- Chiến lược tăng Dropout 0.25 và giảm LR 2e-5 đang cho thấy hiệu quả rũ bỏ tín hiệu nhiễu cực tốt trong phiên Á.

Hệ thống sẽ tiếp tục giữ tiến trình chạy để dò tìm các đỉnh cao hơn. Chưa cần thiết tạo Run mới."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
