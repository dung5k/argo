import subprocess

msg = """🏯 [ASIAN V6 MTF] Báo cáo tình hình State hiện tại: Ổn định.
🔥 Tiến trình Vòng 34 (PID 11836) đang hoạt động!
- Tình trạng: Lượt chạy thử nghiệm khung thời gian 15 phút đang trong giai đoạn nạp dữ liệu. 
- Do hệ thống phải gộp nến từ dữ liệu Tick/1m lên nến 15 phút, đồng thời tạo cửa sổ W12 (tương đương chuỗi dữ liệu 3 tiếng liên tục), quá trình tiền xử lý (Feature Engineering) sẽ mất thêm chút thời gian.

Hệ thống đang kiểm soát hoàn toàn background job. Sẵn sàng chờ lệnh hoặc báo cáo ngay khi có kết quả!"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
