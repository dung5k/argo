# -*- coding: utf-8 -*-
import subprocess

msg = """✅ [CẬP NHẬT CHIẾN THUẬT] Sếp Lê, tôi đã vá xong file Prompt của phiên London!

🔧 Thay đổi thực hiện trên `.agent/periodic_prompt_ltc_london_v6_local.md`:

Đã thêm mục **📋 MẪU BÁO CÁO TELEGRAM BẮT BUỘC** ngay trước phần thông báo cuối. Từ vòng kế tiếp, mỗi chu kỳ định kỳ sẽ TỰ ĐỘNG báo cáo theo cấu trúc chuẩn gồm:
- Trạng thái + Seed mới nhất
- Kết quả chi tiết của Seed vừa hoàn thành (Score, WR@0.80, WR@0.94)
- Bảng tổng kết 6 vòng gần nhất với đầy đủ số liệu thực tế
- Nhận định xu hướng + mục tiêu

Quy tắc bất di bất dịch: Bảng số liệu phải đọc từ Diary thực tế, KHÔNG được bịa số."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
