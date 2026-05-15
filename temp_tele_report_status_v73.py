# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 73 (PID 5800) đang khởi động mẻ lưới mới!
- Tình trạng: Lượt Đào Vàng Holy Grail Lần 39 đang trong giai đoạn tiền xử lý dữ liệu và thiết lập ma trận tensor.
- Tiến độ: Hệ thống đang làm việc hết công suất để chuyển hóa khối lượng dữ liệu khổng lồ trước khi bước vào Epoch đầu tiên.

Cỗ Máy Trạng Thái giữ nguyên hàng rào khóa chặt các tiến trình khác, đảm bảo Vòng 73 được bơm tối đa tài nguyên hệ thống!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
