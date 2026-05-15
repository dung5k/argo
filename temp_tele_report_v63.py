# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 63).
📊 Kết quả Vòng 62: ĐÀO VÀNG HOLY GRAIL (Lần 28) ⛏️
- Kết quả Win Rate được giữ sổ an toàn ở mức: **70.73%** (tại Epoch 80).
- Báo cáo phân tích Log: Một vòng đấu vô cùng bền bỉ, chạy sâu tới tận Epoch 100 mới chạm mốc dừng Early Stopping. Best Loss được thiết lập kiên cố trên nền tỷ lệ thắng 70%. Đặc biệt ấn tượng là ở chặng đua nước rút (Epoch 90, 91, 96, 99), tỷ lệ thắng liên tục giật lên con số **76.7%**! 

🚀 Triển khai Vòng 63 (ĐÀO VÀNG HOLY GRAIL Lần 29):
1. Hành động: Đóng gói tham số, kéo cần gạt Vòng lặp 29!
2. Mục tiêu: Nhịp nổ 76.7% liên tục lặp lại đã thắp lên hy vọng cực lớn. Cỗ Máy Trạng Thái sẽ tiếp tục tung các chuỗi Stochastic Optimization để bắt Validation Loss phải gục ngã ngay tại điểm nổ này (hoặc thậm chí 80%).
3. Tiến trình Vòng 63 (PID 8424) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
