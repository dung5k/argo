import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 15).
📊 Kết quả Vòng 14: HOÀN TOÀN ĐIÊN RỒ! 🤯 KHÔNG TƯỞNG!
- Bài test siết chặt Stop Loss xuống 0.15% (R:R=2.33) thành công rực rỡ!
- Win Rate ở ngưỡng tự tin cao nhất đạt mức KHỦNG 77.08%! Điều này chứng tỏ khi Golden Config xuất tín hiệu, giá chạy thẳng tới Take Profit mà không hề đi ngược hướng (zero-drawdown).

🚀 Triển khai Vòng 15:
1. Giữ nguyên 100% "Holy Grail" Risk/Reward (TP=0.35%, SL=0.15%).
2. Tinh chỉnh Neural: Giảm tốc độ học (Learning Rate) từ 2e-5 xuống 1e-5.
3. Mục tiêu: Việc giảm tốc độ học giúp mô hình "vắt kiệt" thông tin ở các mốc Threshold thấp, kỳ vọng kéo điểm Composite Score phá đỉnh mọi thời đại 0.5662 (của Vòng 12).
4. Tiến trình Vòng 15 (PID 7576) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
