# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 34).
📊 Kết quả Vòng 33: THỬ NGHIỆM TẦM NHÌN 2 GIỜ ⏰
- Việc cung cấp cho AI chuỗi OrderFlow 2 giờ đồng hồ (`W24`) vẫn đạt mức Win Rate cực khủng **75.55%**! Mặc dù hơi lép vế một chút so với 76.59% của góc nhìn 1 giờ (`W12`), nhưng nó là minh chứng thép cho việc biểu đồ 5 phút thực sự là một MỎ VÀNG của phiên Châu Á!
- KẾT LUẬN: Đối với chiến thuật Micro-Scalping (chốt lời cực ngắn 0.35%), dữ liệu OrderFlow vượt quá 1 giờ trong quá khứ là không cần thiết và có thể gây nhiễu nhẹ. `WINDOW_SIZE=12` là tỷ lệ hoàn hảo!

🚀 Triển khai Vòng 34 (KHÁM PHÁ VÙNG ĐẤT 15 PHÚT):
1. Thừa thắng xông lên với bài toán Feature Engineering, ta tiếp tục kéo giãn Timeframe!
2. Hành động: Chuyển dữ liệu đầu vào sang khung **15 phút** (`15min`). Cửa sổ `W12` giờ đây sẽ tương đương với một chuỗi dữ liệu dài tận **3 tiếng đồng hồ**.
3. Mục tiêu: Liệu một bức tranh quá vĩ mô (3 tiếng) có thể giải quyết được bài toán siêu vi mô (bắt sóng ngắn 0.35%) hay không? Đây là một phép thử cực kỳ thú vị để tìm ra ranh giới "Mù màu dữ liệu" của mạng Nơ-ron.
4. Tiến trình Vòng 34 (PID 11836) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
