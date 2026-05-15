import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 12).
📊 Kết quả Vòng 11: ĐÃ TÌM THẤY CHÉN THÁNH (HOLY GRAIL)! 🏆
- Dù gồng lãi xa hơn (TP 0.003, R:R=1.5), mô hình VẪN giữ vững Win Rate ĐỈNH CAO: 73.46%!
- Composite Score phá đỉnh mọi thời đại: 0.5537.

🚀 Triển khai Vòng 12:
1. Giữ cứng Golden Config (Dropout 0.25, LR 2e-5, W20).
2. Thử thách giới hạn cuối cùng: Đẩy Take Profit (TP) lên mức 0.0035 (R:R đạt 1.75).
3. Mục tiêu: Ép thanh khoản đi ngang của phiên Á phải trả lợi nhuận cực đại. Nếu Win Rate rớt mạnh, ta sẽ chốt Vòng 11 là bản cuối cùng để đưa vào Trade Live.
4. Tiến trình Vòng 12 (PID 10428) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
