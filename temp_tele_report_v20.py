import subprocess

msg = """🏯 [ASIAN V6 MTF] Tạo Run Mới (Vòng 20).
📊 Kết quả Vòng 19: CHIẾN THUẬT GỒNG LỖ THẤT BẠI! 📉
- Việc nới rộng Stoploss ra 0.25% không giúp mô hình thở phào, mà ngược lại, nó làm Win Rate rơi tự do xuống 71.42%.
- KẾT LUẬN: Quy luật Micro-Scalping Á là "Vào nhanh, ra nhanh". Nếu lệnh đi ngược hướng 0.15%, động lượng đã chết. Stoploss 0.15% chính là mốc tối hậu không thể lay chuyển!

🚀 Triển khai Vòng 20:
1. Áp dụng lại ngay lập tức mức Stoploss Chân Lý: `0.0015` (0.15%).
2. Đổi chiến thuật sang "Easy Take Profit": Giữ nguyên rủi ro, nhưng hạ kỳ vọng chốt lời xuống một nhịp: từ 0.35% (Vòng 14) xuống `0.0032` (0.32%).
3. Tỷ lệ R:R hạ nhiệt đôi chút về mức 2.13. Đổi lại, mục tiêu chốt lời sẽ dễ chạm hơn rất nhiều. Chờ xem liệu sự dễ dàng này có thể thổi bùng Win Rate xuyên thủng bức tường 80% hay không!
4. Tiến trình Vòng 20 (PID 15060) đã khởi động an toàn. Nhật ký Diary đã được cập nhật."""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
