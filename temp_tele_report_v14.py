import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 14).
📊 Kết quả Vòng 13: ĐÃ CHẠM RANH GIỚI CUỐI CÙNG! ⛔
- Khi đẩy Take Profit lên 0.40%, giá thường bị pullback chặn lại, khiến Win Rate giảm xuống 71.42% và Composite Score thoái lui về 0.5207.
- Kết luận: Cấu hình Vòng 12 (TP=0.35%, SL=0.20%, Win Rate 73%) chính là đỉnh cao nhất của lợi nhuận.

🚀 Triển khai Vòng 14:
1. Quay trở lại mức Take Profit "vàng" 0.0035 của Vòng 12.
2. Bài test độ nhiễu: Bóp chặt Stop Loss (SL) từ 0.0020 xuống 0.0015.
3. Tỷ lệ R:R vọt lên mức 2.33. Mục tiêu là kiểm chứng xem liệu một Stop Loss cực ngắn (0.15%) có dễ bị quét bởi "noise" (độ nhiễu đi ngang) của phiên Á hay không. Nếu Win Rate vẫn trụ vững, đây sẽ là cỗ máy in tiền siêu việt.
4. Tiến trình Vòng 14 (PID 13596) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
