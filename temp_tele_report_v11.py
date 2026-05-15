import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 11).
📊 Kết quả Vòng 10: 
- Việc đổi Feature Engineering trên máy Local không hiệu quả do thiếu dữ liệu Raw Parquet. Mô hình vẫn chạy với mốc Win Rate xuất sắc quanh 69-73%.
- Kết luận: Cấu hình Vòng 8 (Dropout 0.25, LR 2e-5, Window 20) chính thức được đóng băng làm "Golden Config".

🚀 Triển khai Vòng 11:
1. Giữ nguyên Golden Config siêu ổn định.
2. Tối ưu hóa Lợi nhuận (Risk/Reward): Tăng mức Take Profit (TP) từ 0.0025 lên 0.0030 (Đẩy R:R lên mức 1.5).
3. Mục tiêu: Lợi dụng Win Rate khổng lồ (>70%) để gồng lãi dài hơn, tối đa hóa lợi nhuận PnL trong một đêm.
4. Tiến trình Vòng 11 (PID 13124) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
