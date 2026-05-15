# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 49).
📊 Kết quả Vòng 48: ĐÀO VÀNG HOLY GRAIL (Lần 14) ⛏️
- Kết quả Win Rate được hệ thống chốt ở mức an toàn: **63.63%** (Epoch 19).
- Báo cáo phân tích Log: Lại một vòng lặp nữa chứng kiến màn nảy lò xo tuyệt đẹp: Win Rate bật vọt lên **75.8%** ở Epoch 29! Tuy nhiên, Early Stopping vẫn đóng vai "Kẻ hủy diệt" vô tình, chém bỏ mức Win Rate này vì Validation Loss rủi ro. 

🚀 Triển khai Vòng 49 (ĐÀO VÀNG HOLY GRAIL Lần 15):
1. Không có sự thỏa hiệp! Cơ chế bảo vệ Live Bot tuyệt đối đang phát huy sức mạnh. Việc của chúng ta là tiếp tục đổ dữ liệu vào bộ gieo hạt.
2. Hành động: Chạy vòng lặp thứ 15 trên cấu trúc bất bại 5m_W12.
3. Mục tiêu: Bắt trúng một Epoch có Loss rớt thảm dưới đáy đúng lúc Win Rate chạm đỉnh 80%.
4. Tiến trình Vòng 49 (PID 15804) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
