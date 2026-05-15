# -*- coding: utf-8 -*-
import subprocess

msg = """📊 [PHÂN TÍCH CHIẾN THUẬT] Trả lời câu hỏi của Sếp Lê về file Prompt Asian vs London:

Sau khi đọc và so sánh 2 file `periodic_prompt_ltc_asian` và `periodic_prompt_ltc_london`, tôi nhận thấy Prompt London thực ra **khắt khe và nhiều quy tắc hơn** (do có thêm luật No Concurrency, Slow Warmup, Cosine Annealing). 

Tuy nhiên, chính sự tự do của phiên Á đã tạo ra "Chén Thánh" 76.47%. Dưới đây là 3 điểm tinh hoa từ phiên Á nên được đưa sang file Prompt London:

1️⃣ **Nới lỏng gông cùm R:R (Hạ TP/SL):**
- **London hiện tại:** Ép AI chạy R:R rất lớn (1:2 hoặc 1:3, TP=0.008, SL=0.003) cộng thêm luật "Chỉ 1 lệnh/thời điểm". Điều này khiến Bot phải gồng trend rất mệt mỏi giữa các nhịp whipsaw, dẫn đến Win Rate gần đây của London rơi thảm hại (14-32%).
- **Học từ Asian:** Asian cho phép "Micro-Scalping" với TP/SL hẹp (chỉ cần R:R > 1.2). London đánh nhanh rụt nhanh trong các cú giật Breakout sẽ an toàn hơn nhiều so với việc ngâm lệnh. Ta nên hạ yêu cầu R:R của London xuống.

2️⃣ **Thừa kế bộ gen "Chén Thánh" 5m_W12:**
- Phiên Á đã mất rất nhiều thời gian mới mò ra tỷ lệ vàng `Khung 5 phút + Window 12 nến`. Trong khi đó Prompt London hiện vẫn để AI tự do mò mẫm khung 1m (gây nhiễu nặng ở Seed 49-52). 
- Nên hardcode thẳng gợi ý: *"Khởi điểm tìm kiếm từ khung 5m_W12 của phiên Á đã thành công"* vào Prompt London để tiết kiệm thời gian.

3️⃣ **Đề cao tính năng OrderFlow:**
- Prompt Á nhấn mạnh *"Giao dịch Micro-Scalping kết hợp OrderFlow là chìa khóa"*. London thanh khoản cực lớn nên việc đọc OrderFlow (Delta Volume) càng quan trọng hơn để phân biệt Breakout thật hay giả. Nên mang nguyên tắc này sang London.

Sếp có muốn tôi cập nhật ngay những "Tinh hoa" này vào file Prompt của London không ạ? 🛠"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
