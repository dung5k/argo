import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (HolyGrail_212).

📊 Kết quả HolyGrail_211:
- Best Val Loss tại Epoch 79. Composite Score: 0.1014
- Win Rate: 82.24% (Threshold 0.74) | 90.00% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (D64, L3, Dropout 0.25):
| Vòng | Score  | WR@0.74 | WR@0.85 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 210  | 0.1069 | 78.86%  | 96.96%  | N/A     |
| 211  | 0.1014 | 82.24%  | 90.00%  | N/A     |
| 212  | Wait   | Wait    | Wait    | Wait    |

Nhận định ngắn về xu hướng Score/WR: Vòng 212 vừa được kích hoạt cách đây ít phút và hiện đang trong quá trình Warm-up Autoencoder (Epoch 3/10). Việc tăng cường Dropout=0.25 sẽ ép hệ thống rèn luyện vất vả hơn. 🚀 HolyGrail_212 đang chạy! Mục tiêu: Ngăn chặn hội tụ sớm (chống Overfit) để đẩy Win Rate Thực Chiến lên 85% tại Threshold 0.74!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
