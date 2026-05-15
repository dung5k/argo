# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 32).
📊 Kết quả Vòng 31: KỲ TÍCH FEATURE ENGINEERING! 🚀
- Nước đi thay đổi cấu trúc dữ liệu đã mang lại vinh quang! Việc chuyển Base Timeframe sang biểu đồ 5 phút (5min) đã đóng vai trò là một bộ lọc nhiễu tự nhiên tuyệt vời. Mô hình không còn bị rối trí bởi các dao động ngẫu nhiên li ti nữa.
- KẾT QUẢ: Win Rate lập tức bùng nổ lên **76.59%** ngay từ lượt chạy đầu tiên! Tín hiệu cực kỳ chất lượng, vượt xa cái bóng 69% của các vòng lặp 1 phút.

🚀 Triển khai Vòng 32 (XÁC THỰC KHUNG 5 PHÚT):
1. Không ngủ quên trên chiến thắng, hệ thống lập tức kích hoạt đợt Validation Run cho khung 5 phút.
2. Hành động: Lặp lại 100% cấu hình Vòng 31 (`5min, W12, LR 2e-5, Drop 0.25`).
3. Mục tiêu: Xác thực xem liệu 76.59% trên biểu đồ 5 phút là một con số "bình thường mới" (trạng thái dao động tự nhiên nhờ dữ liệu sạch hơn), hay lại là một điểm khởi tạo ngẫu nhiên may mắn. Nếu Vòng 32 tiếp tục giữ phong độ >75%, ta sẽ chính thức lập ngôi vương mới!
4. Tiến trình Vòng 32 (PID 10472) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
