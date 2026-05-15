# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 27).
📊 Kết quả Vòng 26: THẢM HỌA HỌC VẸT (OVERFITTING)! ❌
- Phép thử mở rộng không gian nhúng `D_MODEL` lên 64 đã thất bại hoàn toàn. Do dữ liệu phiên Á quá mỏng và đầy nhiễu, mô hình dư thừa tham số này đã ghi nhớ toàn bộ rác thay vì tìm ra tín hiệu thật. Win Rate tụt dốc không phanh xuống **55.0%**.
- KẾT LUẬN: `D_MODEL=32` là giới hạn vật lý hoàn hảo để ép mạng nơ-ron lọc nhiễu.

🚀 Triển khai Vòng 27 (ARCHITECTURE TUNING - CHIỀU SÂU):
1. Khôi phục `D_MODEL=32` và bảo toàn Golden Config (LR 2e-5, Dropout 0.25).
2. Hành động: Áp dụng triết lý "Occam's Razor" (Dao cạo Ockham) - Hạ số lớp Transformer (`NUM_LAYERS`) từ mức chuẩn 2 xuống **1 lớp duy nhất**.
3. Mục tiêu: Tạo ra một bộ não "siêu mỏng". Nếu phiên Á quá đơn điệu, một mạng nơ-ron cực kỳ đơn giản có thể sẽ miễn nhiễm với nhiễu tốt hơn một mạng lưới sâu. Kỳ vọng Vòng 27 sẽ tái lập lại phép màu 77% nhưng mang lại tốc độ suy luận (Inference) chớp nhoáng cho Live Bot.
4. Tiến trình Vòng 27 (PID 3372) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
