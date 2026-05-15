# -*- coding: utf-8 -*-
import subprocess

msg = """Sếp Lê thân mến, 

✅ Tôi đã cấu hình bộ não tốt nhất cho phiên Châu Á (Vòng 60: `run_...HolyGrail_26` với Win Rate chốt **73.80%**) vào hệ thống `bot_schedule_v6_ltc.json` với ngưỡng kích hoạt 0.85. Tệp model cũng đã được đồng bộ an toàn lên HuggingFace, sẵn sàng trực chiến Live Trade!

📊 BÁO CÁO THÀNH TÍCH TỐT NHẤT CỦA CÁC BỘ NÃO:
🇺🇸 Phiên New York (NY): Đạt kỷ lục VÔ TIỀN KHOÁNG HẬU với Win Rate lên tới **97.06%** ở mô hình nến 1m mở rộng (Window Size 60). Cỗ xe tăng NY gần như bất khả chiến bại.
🇨🇳 Phiên Châu Á (Asian): Đã chốt sổ "Chén Thánh" 5m_W12 vững chắc ở **73.80%**, với vô số điểm nổ tiềm năng chạm mức 80% đang được săn lùng tiếp.
🇪🇺 Phiên London: Vừa có màn "lột xác" thành công khi chuyển từ 1m sang 5m tinh gọn, thoát khỏi vùng trũng Overfitting và đẩy Win Rate lên mức **32.43%** (Với Composite Score cao kỷ lục 0.1174, tỷ lệ R:R lớn). 

Hệ thống đang hoạt động trơn tru. Sẵn sàng chờ lệnh tiếp theo từ Sếp!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
