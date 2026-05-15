# -*- coding: utf-8 -*-
import subprocess

msg = """✅ [BUG FIX XAG] Sếp Lê, tôi đã kiểm tra và xử lý dứt điểm lỗi ngắt tín hiệu Output của Bot Live XAG!

🔍 NGUYÊN NHÂN LỖI:
- Cấu hình Scaler của V5 XAG yêu cầu phân tích dữ liệu vĩ mô từ Crypto (gồm `BTCUSDm` và `ETHUSDm`).
- Tuy nhiên, tệp `bot_config_xag.json` cũ lại thiếu khai báo nguồn cấp 2 mã này. Nghiêm trọng hơn, trên terminal MT5 Exness, 2 cặp Crypto này đang bị ẩn khỏi bảng giá (Market Watch).
- Do đó dữ liệu trả về bị rỗng (NaN), khiến Mạng Nơ-ron từ chối xử lý để bảo vệ an toàn.

🛠 CÁCH KHẮC PHỤC:
1. Tôi đã vá tệp cấu hình XAG, bổ sung luồng định tuyến (Routing) để ép bot lấy tín hiệu BTC và ETH.
2. Tôi đã can thiệp thẳng vào hệ thống lõi MT5 bằng Python để bật ép buộc (Force Enable) 2 mã `BTCUSDm` và `ETHUSDm` lên Market Watch.
3. Đã làm sạch tiến trình và theo dõi log. Pipeline V3 đã thông suốt trở lại! Mạng Nơ-ron đã xuất ra Output bình thường (đang cho tín hiệu HOLD).

Con rồng XAG đã tỉnh giấc và tiếp tục tham chiến song hành cùng LTC! 🛡"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
