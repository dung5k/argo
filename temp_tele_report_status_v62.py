# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 62 (PID 4200) đang cày ải miệt mài!
- Tình trạng: Lượt Đào Vàng Holy Grail Lần 28 vừa mới bắt đầu. Hệ thống đang tiến hành nạp Tensor và chuẩn bị khởi động các Epoch đầu tiên.
- Tiến độ: Sau 2 vòng liên tiếp chốt sổ kỷ lục 73.80%, toàn bộ nguồn lực tính toán đang được dồn tối đa cho mẻ lưới mới này.

Cỗ Máy Trạng Thái đang thiết lập vòng vây bảo vệ, nghiêm cấm mọi tiến trình khác chen ngang để đảm bảo tính toàn vẹn của dữ liệu!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
