# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 57 (PID 14724) đang cày ải miệt mài!
- Tình trạng: Lượt Đào Vàng Holy Grail Lần 23 đang huấn luyện ở Epoch 22.
- Tín hiệu sớm: Cỗ máy vừa phá vỡ một đáy Validation Loss mới ở Epoch 18 với Win Rate tuyệt vời: **72.22%**. Thuật toán vẫn đang tiếp tục chạy để thăm dò các Epoch sâu hơn, hy vọng sẽ một lần nữa chạm đến đỉnh 80% Win Rate ở phía cuối đường hầm!

Hệ thống đang bảo vệ luồng chạy ngầm này tuyệt đối, không cho phép bất kỳ tiến trình nào khác chen ngang. Cỗ Máy Trạng Thái tiếp tục giữ nguyên nhịp độ giám sát!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
