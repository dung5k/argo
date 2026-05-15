# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 23).
📊 Kết quả Vòng 22: CHIẾN THUẬT SLOW WARMUP THẤT BẠI! ❌
- Việc kéo dãn thời gian khởi động lên 30 epoch đã phá hỏng gia tốc của thuật toán OneCycleLR. Mô hình không đủ động lượng để bứt phá và bị mắc kẹt ở cực tiểu kém, Win Rate rớt xuống đáy 70.0%.
- KẾT LUẬN: Chu kỳ `WARMUP_EPOCHS = 15` là điểm cân bằng hoàn hảo và không được phép thay đổi!

🚀 Triển khai Vòng 23:
1. Quay trở lại các chỉ số cốt lõi: TP 0.35%, SL 0.15%, Dropout 0.25, Warmup 15.
2. Áp dụng chiến thuật "Gia tốc nhẹ": Tăng `Learning Rate` từ mốc Vàng 2e-5 lên **3e-5**.
3. Mục tiêu: Nhằm khắc phục tính ngẫu nhiên của bộ trọng số, việc cung cấp thêm một chút tốc độ học sẽ giúp mô hình có thêm "động năng" để thoát khỏi các vùng cực tiểu 72%, kỳ vọng nó sẽ rơi thẳng vào "siêu cực tiểu" 77.08% của Vòng 14 một cách nhất quán.
4. Tiến trình Vòng 23 (PID 3196) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
