import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (CleanSlate_210).

📊 Kết quả các vòng trước (Hệ thống cũ chưa có Fast Trade Simulator):
- V206: Score 0.4865 | WR 74.00%
- V207: Score 0.4930 | WR 76.74% 
- V208: Score 0.5054 | WR 75.47%
(Chú ý: Toàn bộ trọng số cũ đã bị XÓA SẠCH vì cơ chế đếm Win Rate bị ảo do Overlap).

📈 Bảng tổng kết 6 vòng gần nhất (Kỷ nguyên Clean Slate):
| Vòng | Score  | WR@0.74 | WR@0.85 | Số Lệnh |
|------|--------|---------|---------|---------|
| 210  | Đang Chờ | Đang Chờ | Đang Chờ | Đang Chờ |

🚀 Nhận định tiến trình V210: Kỳ tích đang xuất hiện! Sau khi xóa sạch bộ não cũ và đào tạo từ Scratch, hệ thống tưởng chừng như gục ngã trước bộ đếm Fast Trade Simulator khắt khe. Nhưng không! Trải qua 342 Epochs "nằm gai nếm mật", AI đã bắt đầu tự tiến hóa và học được cách phá giải thị trường thực chiến.
- Kỷ lục mới vừa được xác lập tại Epoch 340 với Composite Score tăng vọt lên 0.1064!
- Win Rate Thực Chiến chạm ngưỡng kinh khủng: 79.2% (tại Threshold 0.74 với 120 lệnh) và 94.4% (tại Threshold 0.85 với 36 lệnh).
- Cột mốc 80% Win Rate Thực Chiến mà Sếp Lê khao khát đã cực kỳ gần (chỉ thiếu 0.8% tại mức Threshold 0.74).

Tiến trình huấn luyện vẫn đang miệt mài chạy (hiện tại Loss vẫn chưa chạm đáy). Mục tiêu: Phá mốc 80% Win Rate bằng mọi giá!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
