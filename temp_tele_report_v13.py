import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 13).
📊 Kết quả Vòng 12: KỶ LỤC MỚI ĐƯỢC THIẾT LẬP! 🏆
- Việc ép Take Profit lên mốc 0.35% (R:R=1.75) không thể làm khó Golden Config.
- Win Rate giữ vững ở mức 73.07%.
- Composite Score tiếp tục phá đỉnh: 0.5662!

🚀 Triển khai Vòng 13:
1. Thử thách siêu hạn: Đẩy Take Profit (TP) lên mốc 0.0040 (tức là 0.40%).
2. Tỷ lệ Risk/Reward chính thức đạt mức lý tưởng 2.0 (TP=0.4%, SL=0.2%).
3. Mục tiêu: Tìm xem liệu biến động chậm chạp của phiên Á có thể cho phép giá "chạy một lèo" 0.4% mà không bị quét Stoploss hay không. Đây sẽ là phép thử cuối cùng cho khía cạnh R:R.
4. Tiến trình Vòng 13 (PID 5384) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
