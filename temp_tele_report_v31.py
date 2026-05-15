# -*- coding: utf-8 -*-
import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 31).
📊 Kết quả Vòng 30: ĐÀO VÀNG BẾ TẮC! ❌
- Win Rate tiếp tục găm chặt ở mức tự nhiên **69.76%**.
- KẾT LUẬN: Việc thụ động cắm máy chạy lặp lại cấu hình Vàng để trông chờ vào "luật số lớn" nảy ra hạt giống Win Rate 77% là quá lãng phí tài nguyên máy chủ. Ta phải chủ động tạo ra đột phá!

🚀 Triển khai Vòng 31 (FEATURE ENGINEERING - BƯỚC NGOẶT LỚN):
1. **ĐÌNH CHỈ STOCHASTIC MINING!** Chuyển trọng tâm sang chế độ cấu trúc dữ liệu đầu vào (Feature Engineering).
2. Hành động: LẦN ĐẦU TIÊN CẤT BƯỚC ĐỔI TIMEFRAME! Chuyển đổi khung thời gian (Base Timeframe) của ma trận dữ liệu từ `1min` sang **`5min`**. Đồng thời, hạ `WINDOW_SIZE` từ 20 xuống **12** (tương đương với 60 phút - 1 giờ OrderFlow).
3. Mục tiêu: Khung 1 phút của phiên Á chứa toàn "nhiễu vi mô" (Micro Noise) đánh lừa mạng Nơ-ron. Bằng cách gộp nến thành 5 phút, ta tự động tạo ra một bộ lọc nhiễu tự nhiên (Low-Pass Filter). Kỳ vọng hệ thống sẽ kiến tạo ra một bản đồ học thuật (Loss Landscape) hoàn toàn mới, vượt mặt cấu hình Vàng 1 phút huyền thoại!
4. Tiến trình Vòng 31 (PID 15552) đã khởi động rầm rộ. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
