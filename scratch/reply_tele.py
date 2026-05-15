import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '.agent'))
try:
    import send_to_tele
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '.agent'))
    import send_to_tele

msg = """Dạ Sếp Lê, Sếp đã chỉ ra một vấn đề cực kỳ cốt lõi trong Algo Trading: **Độ lệch pha giữa Training và Live Trade**. Winrate lúc Train > 80% nhưng Live lại bị "ăn vả" thường đến từ 3 nguyên nhân chính sau:

1️⃣ **Rò rỉ dữ liệu (Data Leakage / Look-ahead Bias)**: Quá trình tạo nhãn (Labeling) hoặc chuẩn hóa (Scaler) vô tình dùng dữ liệu của nến tương lai. Lúc Train kết quả ảo, nhưng ra Live không có nến tương lai nên bot bắt sai.
2️⃣ **Lệch pha bộ mồi dữ liệu (Warm-up Bias)**: Lúc Live, bot chỉ gọi 1500 nến để tính EMA, RSI, MACD. Trong khi lúc Train lại dùng nguyên bộ data 2 năm. Các chỉ số dài hạn bị tính sai số so với lúc train.
3️⃣ **Độ trễ khớp lệnh & Trượt giá (Slippage)**: Scalping biên độ cực mỏng (ví dụ TP 0.4%), nhưng Live tốn 2-3s để chạy xong AI Pipeline, giá chạy mất 0.2% -> Triệt tiêu lợi thế.

🛠 **KẾ HOẠCH ĐIỀU TRA (Cần Sếp duyệt):**
Em đề xuất thực hiện **Kiểm tra độ nguyên vẹn Tensor (Data Integrity Test)**:
- Em sẽ viết 1 script lấy 1500 nến raw cũ, cho chạy qua quy trình Live (`DataProcessorV3`) để tạo ra Tensor A.
- Lấy Tensor B đã lưu sẵn từ tập Training.
- So khớp 2 Tensor tại cùng một mốc thời gian. Nếu có sai số, chứng tỏ Logic tính toán/Scaler giữa Train và Live đang không đồng nhất!

Sếp có đồng ý để em bắt tay vào code script kiểm tra (So khớp Tensor A và B) ngay bây giờ không ạ?"""

send_to_tele.send_to_telegram(msg, is_done=True, target_channels='1816854047')
