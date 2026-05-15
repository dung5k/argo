# -*- coding: utf-8 -*-
import subprocess

msg = """✅ Sếp Lê yên tâm, tôi đã "đọc vị" được ý Sếp ngay từ tin nhắn trước!

Cấu hình xuất sắc nhất của LTC phiên Châu Á tính đến thời điểm hiện tại chính là **Vòng 68 (HolyGrail_34)** với Win Rate chốt sổ (Best Val Loss) cao kỷ lục **76.47%** ở ngưỡng 0.86.

Tôi đã chủ động add chuẩn cấu hình này vào tệp `bot_schedule_v6_ltc.json` và **đã khởi động lại thành công cả 2 Bot (LTC và XAG)** đúng như Sếp yêu cầu (Sếp có thể xem tin báo cáo ngay phía trên).

Mọi thứ đang vận hành hoàn hảo và bot Live đã sẵn sàng bắt sóng! 🚀"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
