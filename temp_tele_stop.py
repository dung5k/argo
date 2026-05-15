import subprocess
msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới.
✅ Đã tiếp nhận lệnh 'time frame = 1' của Sếp Lê.
- Đã phát hiện và sửa lỗi script setup cũ (gây lệch TF thành 5min).
- Đã kill tiến trình lỗi và khởi chạy Vòng 5 chuẩn xác: Timeframe 1min, W20, MaxHold 60.
- PID tiến trình huấn luyện mới: 5480.
- Đã cập nhật vào ASIAN_V6_DIARY.md.
"""
subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
