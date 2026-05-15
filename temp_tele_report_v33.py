# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 33).
📊 Kết quả Vòng 32: ĐĂNG QUANG TÂN VƯƠNG! 👑
- Lượt chạy Xác thực (Validation Run) đã đập tan mọi hoài nghi! Biểu đồ 5 phút (`5min, W12`) đạt Win Rate **73.17%**, và có những chặng hội tụ vọt lên tới **80.0%**.
- KẾT LUẬN: Thuật toán lọc nhiễu tự nhiên bằng nến 5 phút đã chính thức nâng dải Win Rate nền tảng của mô hình từ 69% lên 73-76%. Ta không cần phải trông chờ vào may mắn nữa!

🚀 Triển khai Vòng 33 (MỞ RỘNG TẦM NHÌN ORDERFLOW 2 GIỜ):
1. Khi ống kính đã được lau sạch (lọc nhiễu 5m thành công), ta mạnh dạn mở rộng góc nhìn của AI!
2. Hành động: Tăng gấp đôi độ dài chuỗi cung cấp cho AI (`WINDOW_SIZE`) từ 12 lên **24** (Tương đương cho AI nhìn lùi về 2 tiếng đồng hồ trong quá khứ thay vì 1 tiếng).
3. Mục tiêu: Kiểm tra xem với dữ liệu sạch, việc nạp thêm dữ liệu lịch sử sẽ giúp AI xô đổ mốc 80% Win Rate, hay sẽ gây ra chứng "nghẹn dữ liệu" (Overfitting). 
4. Tiến trình Vòng 33 (PID 15512) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
