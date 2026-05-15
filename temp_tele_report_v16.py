import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 16).
📊 Kết quả Vòng 15: PHÉP THỬ THẤT BẠI! ❌
- Việc giảm tốc độ học (LR=1e-5) khiến mô hình phản ứng quá chậm với độ nhiễu. Win Rate tụt lùi về 75.0% và Composite Score giảm còn 0.5495.
- Kết luận cứng: `Learning Rate = 2e-5` là tốc độ hoàn mỹ nhất cho phiên Á.

🚀 Triển khai Vòng 16:
1. Quay về ngay cấu hình Vàng: `LR = 2e-5`.
2. Tiếp tục sử dụng siêu tỷ lệ lợi nhuận R:R = 2.33 (Take Profit = 0.35%, Stop Loss = 0.15%).
3. Bài test cuối cùng: Vi chỉnh nhẹ Dropout giảm từ 0.25 xuống 0.20. Với mức SL cực kỳ eo hẹp, việc giữ lại nhiều nơ-ron hơn (ít dropout hơn) có thể giúp mô hình ghi nhớ các mô hình "cứa SL" (stop hunt) để né tránh chúng. 
4. Tiến trình Vòng 16 (PID 1504) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
