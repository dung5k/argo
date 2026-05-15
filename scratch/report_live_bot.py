import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '.agent'))
try:
    import send_to_tele
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), '.agent'))
    import send_to_tele

msg = """Dạ Sếp Lê, em xin đính chính báo cáo về LOG CỦA TRADE BOT (Giao dịch thực tế/ảo, không phải training):

Sau khi rà soát lại toàn bộ hệ thống file log, em báo cáo tình hình Trade Bot LTC theo các phiên như sau:

📉 TÌNH TRẠNG CHUNG: TRADE BOT LTC ĐANG NGỪNG HOẠT ĐỘNG
- Từ ngày 04/05/2026 đến nay, Trade Bot LTC KHÔNG thực hiện bất kỳ giao dịch nào và không có log hoạt động ở cả 3 phiên (Á, Âu, Mỹ).
- Không có bất kỳ lệnh Buy/Sell nào được ghi nhận trong lịch sử.

🔍 CHI TIẾT LOG GẦN NHẤT:
- Lần cuối cùng Trade Bot LTC được kích hoạt là vào phiên Mỹ (Lúc 20:34 ngày 04/05/2026 - file `trade_bot_ltc.log`). Lúc đó bot khởi tạo não V3 thành công, đồng bộ dữ liệu Vĩ mô (BTC, ETH, BCH...) và đưa ra quyết định "HOLD" (Chờ đợi).
- Ngay sau thời điểm đó, bot đã ngừng ghi log.
- Trong những ngày gần đây (ví dụ log ngày 08/05/2026), hệ thống chỉ ghi nhận log của bot XAG/XAU (và đang bị lỗi Scaler), hoàn toàn vắng bóng tiến trình của LTC.

📌 KẾT LUẬN: 
Trong vài ngày qua, Trade Bot LTC không hề chạy ở bất kỳ phiên nào (Á, Âu, Mỹ). Sếp có muốn em kiểm tra lại bộ lập lịch (Scheduler) và kích hoạt khởi động lại bot Trade LTC không ạ?"""

send_to_tele.send_to_telegram(msg, is_done=True, target_channels='1816854047')
