import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (The Final Push 208).

📊 Kết quả Assassin_207:
- Best Val Loss tại Epoch 4. Composite Score: 0.4930
- Win Rate: 69.40% (Threshold 0.77) | 76.74% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất (Hành trình 80%):
| Vòng | Score  | WR@0.77 | WR@0.90 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 203  | 0.4843 | 64.70%  | 74.07%  | 45.5%   |
| 204  | 0.4497 | 62.90%  | 68.89%  | 45.5%   |
| 205  | 0.4709 | 66.18%  | 72.34%  | 45.5%   |
| 206  | 0.4865 | 66.46%  | 74.00%  | 45.5%   |
| 207  | 0.4930 | 69.40%  | 76.74%  | 45.5%   |
| 208  | Đang Chờ | Đang Chờ | Đang Chờ | 45.5%   |

Chiến dịch Sát Thủ (Vòng 208) đang hoạt động hết công suất! Nhờ hạ Learning Rate xuống 1e-5 để ép mô hình học sâu, AI đã không vội vã chốt non ở Epoch 4 như vòng trước. Kỷ lục Score mới (0.5054) đã được thiết lập ngay tại Epoch 11 với Win Rate đạt 75.5% và quỹ đạo học tập vẫn đang cắm mỏ đi lên rất mượt mà. 🚀 FinalPush_208 đang chờ hội tụ! Mục tiêu: Khoan thủng 80% Win Rate!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
