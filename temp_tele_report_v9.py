import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 9).
📊 Kết quả Vòng 8: KỲ TÍCH ĐÃ XUẤT HIỆN!
- Đạt Composite Score: 0.5219
- Win Rate: 73.81% (Đã đục thủng và vượt xa mục tiêu 70% mong đợi!)
- Dừng sớm tại Epoch 41.

🚀 Triển khai Vòng 9:
1. Phép thử cực hạn: Đẩy Dropout lên mức kịch trần 0.30 và hạ Learning Rate xuống mức tối thiểu 1e-5.
2. Mục tiêu: Kiểm chứng xem việc "ép cực hạn" này có tạo ra sự hội tụ hoàn hảo hơn nữa không, hay sẽ làm giảm khả năng học. Đây là bài test giới hạn cuối cùng cho cấu hình V6 MTF 1min.
3. Tiến trình Vòng 9 (PID 1820) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
