import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 17).
📊 Kết quả Vòng 16: LỖI OVERFITTING NHẸ! 📉
- Việc giảm Dropout xuống 0.20 khiến mô hình bị nhạy cảm với các cấu trúc nhiễu siêu nhỏ của phiên Á. Win Rate tụt lùi thê thảm về mức 72.34%.
- Kết luận: Với Stoploss siêu ngắn 0.15%, mô hình CẦN được tổng quát hóa mạnh hơn để tránh bị "nhầm lẫn" tín hiệu.

🚀 Triển khai Vòng 17:
1. Phục hồi tốc độ học chân ái: `LR = 2e-5`.
2. Giữ nguyên tỷ lệ R:R trong mơ: 2.33 (Take Profit = 0.35%, Stop Loss = 0.15%).
3. Hành động cốt lõi: Tăng Dropout lên kịch trần 0.30. Bằng cách tắt đi 30% nơ-ron ngẫu nhiên, mô hình bị ép phải học các đặc trưng OrderFlow vững chắc nhất, từ đó lách qua các bẫy giá dễ dàng hơn.
4. Tiến trình Vòng 17 (PID 14372) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
