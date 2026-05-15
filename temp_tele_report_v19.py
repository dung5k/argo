import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 19).
📊 Kết quả Vòng 18: ĐÃ VƯỢT GIỚI HẠN VẬT LÝ! 📉
- Việc ép Stoploss xuống 0.12% khiến mô hình bị văng ra khỏi các giao dịch tốt do dính phải "nhiễu" tự nhiên của thị trường (spread, wicks). Win Rate giảm xuống 75.60%.
- KẾT LUẬN CUỐI CÙNG: Cấu hình Vòng 14 (TP 0.35%, SL 0.15%, R:R=2.33, Win Rate 77.08%) là cấu hình mang lại lợi nhuận siêu việt nhất và chính thức được phong thánh là HOLY GRAIL.

🚀 Triển khai Vòng 19:
1. Đổi chiến thuật 180 độ: "Max Breathing Room" (Không Gian Thở Tối Đa).
2. Thiết lập R:R ngay tại biên giới giới hạn: Take Profit = 0.30%, Stop Loss nới rộng lên tới 0.25% (R:R = 1.2).
3. Mục tiêu: Cung cấp cho thuật toán "Chén Thánh" một khoảng lùi rộng rãi để gồng qua các nhịp rung lắc của phiên Á, từ đó tìm kiếm câu trả lời liệu Win Rate có thể bứt phá lên trên mốc 80% hay không.
4. Tiến trình Vòng 19 (PID 12888) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
