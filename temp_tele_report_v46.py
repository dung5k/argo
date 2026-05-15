# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 46).
📊 Kết quả Vòng 45: ĐÀO VÀNG HOLY GRAIL (Lần 11) ⛏️
- Kết quả Win Rate được chốt sổ ở mốc **68.18%**.
- Báo cáo phân tích Log: Tương tự như vòng trước, dù thuật toán đã bung sức lên tới **75.7%** tại Epoch 33, cơ chế Early Stopping vẫn quyết định chốt ở Epoch 7 (nơi Loss thấp nhất). Đây là minh chứng rõ ràng cho nguyên tắc hoạt động: Đặt sự sống còn của tài khoản Live lên trên mọi thứ. Hệ thống thà vứt bỏ một Win Rate cao còn hơn đưa vào một cấu hình có nguy cơ Overfitting.

🚀 Triển khai Vòng 46 (ĐÀO VÀNG HOLY GRAIL Lần 12):
1. Không lùi bước! Cấu hình 5 phút, Cửa sổ 12 vẫn là chân ái.
2. Hành động: Bấm nút khởi chạy Lần 12.
3. Mục tiêu: Cỗ máy quay xổ số tự động lại bắt đầu quay. Những dao động liên tục gần đây là dấu hiệu cho thấy điểm nổ đang ở rất gần!
4. Tiến trình Vòng 46 (PID 7544) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
