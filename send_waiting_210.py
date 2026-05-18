import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (CleanSlate_210).

📊 Kết quả các vòng trước (Hệ thống cũ chưa có Fast Trade Simulator):
- V206: Score 0.4865 | WR 74.00%
- V207: Score 0.4930 | WR 76.74% 
- V208: Score 0.5054 | WR 75.47%
(Chú ý: Toàn bộ trọng số cũ đã bị XÓA SẠCH vì cơ chế đếm Win Rate cũ bị ảo do Overlap).

📈 Bảng tổng kết 6 vòng gần nhất (Kỷ nguyên Clean Slate):
| Vòng | Score  | WR@0.80 | WR@0.86 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 210  | Đang Chờ | Đang Chờ | Đang Chờ | Đang Chờ |

Nhận định tiến trình V210: Đây là vòng đầu tiên được đào tạo từ số 0 (Scratch) với bộ đếm Fast Trade Simulator trung thực nhất. Vì không được kế thừa, mạng neural đang phải vất vả học lại từ đầu (Epoch 63, Score hiện tại ~0.0461, Win Rate ~68.8% tại ngưỡng 0.69). Quỹ đạo Loss đang hội tụ dần dần. Bộ đếm mới đang cực kỳ khắt khe trong việc chặn các lệnh Overlap (chỉ còn khoảng 30 lệnh hợp lệ). AI vẫn đang tiếp tục vật lộn để phá vỡ giới hạn này! 🚀 CleanSlate_210 đang chạy! Mục tiêu: Xây dựng lại đế chế với Win Rate Thực Chiến!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
