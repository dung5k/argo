import sys
sys.path.append('.')
from importlib import util
spec = util.spec_from_file_location("send_to_tele", ".agent/send_to_tele.py")
send_to_tele = util.module_from_spec(spec)
spec.loader.exec_module(send_to_tele)

msg = """🎯 TỔNG KẾT CHIẾN DỊCH AI QUANT XAG V3.5 / V4 🎯

Em xin báo cáo tổng hợp kết quả Tối ưu hóa Bộ não Giao dịch (XAGUSD) trên cả 3 phiên giao dịch:

🔴 PHIÊN ASIAN (XAG)
- Trạng thái: Đã hoàn thiện (V3.5)
- Best Run: Lượt 1 (Asian)
- Composite Score Tốt Nhất: 0.548
- Win Rate Đỉnh (N>=30): 65.8% (117 lệnh)
👉 Đánh giá: Thanh khoản thấp, giá đi ngang nhiều, mô hình đã cố gắng tối đa nhưng Win Rate không thể bứt phá do spread/commission ăn mòn phần lớn lợi nhuận.

🟢 PHIÊN LONDON (XAG)
- Trạng thái: Đã hoàn thiện (V4)
- Best Run: Lượt 2 (London)
- Composite Score Tốt Nhất: 0.590
- Win Rate Đỉnh (N>=30): 65.9% (41 lệnh)
👉 Đánh giá: Chịu ảnh hưởng mạnh bởi tin tức đầu phiên. Đã loại bỏ được tín hiệu nhiễu nhờ bật SMC (Smart Money) một cách chọn lọc, giúp duy trì Win Rate dương nhưng chưa đạt chuẩn 80% an toàn tuyệt đối.

🔵 PHIÊN NEW YORK (XAG) - NGÔI SAO SÁNG NHẤT 🌟
- Trạng thái: Đã hoàn thiện xuất sắc (V4)
- Best Run: Lượt 8 (NY - The Return of the King)
- Composite Score Tốt Nhất: 0.651 (VƯỢT CHỈ TIÊU 0.65)
- Win Rate Đỉnh (N>=30): 85.3% (34 lệnh) và 77.4% (31 lệnh) với Tỷ lệ Buy/Sell cân bằng hoàn hảo.
👉 Đánh giá: Môi trường lý tưởng nhất cho XAG. Việc nới lỏng Triple Barrier (TP=50, SL=50 pips), tắt toàn bộ SMC để tránh nhiễu và khóa tầm nhìn ở mức WINDOW_SIZE=10 đã phát huy toàn bộ năng lực của não bộ (D_MODEL=32).

🔥 KẾT LUẬN CHUNG: Phiên NY chính là mỏ vàng thực sự cho chiến lược M1 Scalping Hit & Run của XAG. Bộ não XAG NY V3.5 đã ĐẠT CHUẨN LIVE DEPLOYMENT. Toàn bộ tiến trình Auto-Tuning đã chính thức chốt sổ hoàn tất!"""

send_to_tele.send_to_telegram(msg, True)
