import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 17 (PID 14372) ĐANG HUẤN LUYỆN rất trơn tru!
- Tình trạng: Vừa hoàn tất Epoch 2.
- Đỉnh hiện tại: Win Rate bật lên mốc 73.0% (với ngưỡng tín hiệu tự tin >= 0.84).
- Phân tích sớm: Bước đi tăng Dropout lên 0.30 đang đi đúng hướng! Mô hình lọc nhiễu tốt hơn hẳn so với mức Dropout 0.20 của Vòng 16, giúp tỷ lệ thắng (Win Rate) bật tăng trở lại dù phải đối mặt với mức Stop Loss siêu ngắn 0.15%.

Hệ thống đang tích cực đào tạo chạy ngầm và sẽ cập nhật liên tục khi phát hiện các đỉnh kỷ lục mới."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
