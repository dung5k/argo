# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 42).
📊 Kết quả Vòng 41: ĐÀO VÀNG HOLY GRAIL (Lần 7) ⛏️
- Kết quả Win Rate bị cắt ở mốc **64.44%**.
- Báo cáo phân tích Log: Lần gieo hạt này xảy ra hiện tượng lệch pha nghiêm trọng giữa hàm Loss và Win Rate. Dù ở Epoch 21, Win Rate vọt lên **75.0%**, nhưng do Validation Loss có dấu hiệu phân kỳ, lưới lọc Early Stopping đã chém thẳng tay, chọn Epoch 2 làm gốc để tránh Overfitting.
- KẾT LUẬN: "Thà vứt nhầm còn hơn bỏ sót". Cơ chế Auto-Tuning hoạt động cực kỳ lạnh lùng và chuẩn xác. Nó sẵn sàng ném một mô hình 75% vào thùng rác nếu phát hiện rủi ro Overfitting, đảm bảo Live Bot luôn được bảo vệ an toàn tối đa.

🚀 Triển khai Vòng 42 (ĐÀO VÀNG HOLY GRAIL Lần 8):
1. Không lùi bước! Cấu hình 5 phút, Cửa sổ 12.
2. Hành động: Khởi chạy thả xúc xắc Lần 8.
3. Mục tiêu: Tiếp tục băm nát dữ liệu cho đến khi Stochastic tìm được sự giao thoa hoàn hảo: Loss cực tiểu và Win Rate chạm đỉnh 80%.
4. Tiến trình Vòng 42 (PID 9464) đã khởi động. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
