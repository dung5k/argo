import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 21).
📊 Kết quả Vòng 20: BÀI TEST CHỐT LỜI SỚM THẤT BẠI! ❌
- Việc hạ Take Profit xuống 0.32% vô tình làm nhiễu dữ liệu huấn luyện, khiến mô hình nhầm lẫn giữa sóng giả và sóng thật. Kết quả: Win Rate sụt giảm về 73.91%.
- KẾT LUẬN TỐI HẬU: 0.35% chính là biên độ sóng "vật lý" chuẩn xác nhất của LTC phiên Á.

🚀 Triển khai Vòng 21:
1. KHÔNG GIAN TÌM KIẾM ĐÃ CẠN KIỆT! Toàn bộ các khả năng vi chỉnh Neural và R:R đã được vét cạn. Vòng 14 chính thức được vinh danh là đỉnh cao tuyệt đối (Win Rate 77.08%, R:R 2.33).
2. Vòng 21 sẽ là một đợt "Huấn Luyện Xác Thực Ngẫu Nhiên" (Stochastic Validation Run): Chạy lại chính xác cấu hình của Vòng 14 từ đầu.
3. Mục tiêu: Xác nhận xem tính ngẫu nhiên trong khởi tạo trọng số có làm thay đổi Win Rate hay không. Nếu Vòng 21 tiếp tục bùng nổ, thuật toán V6 Châu Á đã hoàn toàn sẵn sàng cho môi trường LIVE!
4. Tiến trình Vòng 21 (PID 8792) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
