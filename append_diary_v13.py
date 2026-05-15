import codecs

diary_text = """
### Tóm tắt Vòng 12 (Tăng Take Profit lên 0.0035, R:R=1.75):
- **Kết quả:** Thêm một kỷ lục mới bị phá vỡ! Mô hình đạt Composite Score **0.5662** và Win Rate **73.07%** (chỉ giảm cực kỳ nhẹ so với 73.46% ở Vòng 11).
- **Phân tích Sâu:** Việc ép thanh khoản phiên Á phải đi xa hơn (0.35%) vẫn không làm chùn bước Golden Config. Thuật toán đã chọn lọc các điểm vào lệnh (entry points) quá xuất sắc, giúp giá chạm TP trước khi dính SL. 

### Ý tưởng tiếp theo (Vòng 13):
- **Hành động:** Tiếp tục giữ cứng Golden Config. Đẩy Take Profit lên mốc **0.0040** (tương đương 0.40%), thiết lập R:R ở mức lý tưởng **2.0**.
- **Mục tiêu:** Đây có thể là giới hạn cuối cùng của biến động phiên Á. Thông thường, một nến 1m ở phiên Á rất hiếm khi kéo được dải 0.4% mà không đảo chiều (pullback). Nếu mô hình vẫn trụ được Win Rate > 65% ở mốc R:R=2.0 này, đây sẽ là cấu hình có PnL khổng lồ nhất lịch sử.
"""

with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)
