import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 10).
📊 Kết quả Vòng 9: 
- Win Rate giảm nhẹ xuống 71.79% khi ép Dropout lên kịch trần.
- Phân tích: Giới hạn Regularization đã được xác định. Cấu hình Vòng 8 (Dropout 0.25, LR 2e-5) chính thức là "Điểm Ngọt" (Golden Configuration) tối ưu nhất cho cấu trúc Neural.

🚀 Triển khai Vòng 10:
1. Khóa cứng Golden Config của Vòng 8.
2. Bắt đầu giai đoạn Tối Ưu Hóa Đầu Vào (Feature Engineering). Nới rộng `WINDOW_SIZE` từ 20 lên 30 (tăng khả năng nhìn lại quá khứ lên 30 phút).
3. Mục tiêu: Giúp AI bắt được momentum xu hướng rõ ràng hơn, kỳ vọng đục thủng mốc Win Rate 75%.
4. Tiến trình Vòng 10 (PID 2844) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
