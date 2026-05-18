import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (TheBreakthrough_206).

📊 Kết quả EagleEyes_205:
- Best Val Loss tại Epoch 24. Composite Score: 0.4709
- Win Rate: 66.18% (Threshold 0.77) | 72.34% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất (Dung hợp W24 + Attention):
| Vòng | Score  | WR@0.77 | WR@0.90 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 201  | 0.2230 | 40.82%  | N/A     | 45.5%   |
| 202  | 0.4723 | 62.65%  | 68.96%  | 45.5%   |
| 203  | 0.4843 | 64.70%  | 74.07%  | 45.5%   |
| 204  | 0.4497 | 62.90%  | 68.89%  | 45.5%   |
| 205  | 0.4709 | 66.18%  | 72.34%  | 45.5%   |
| 206  | Đang Chờ | Đang Chờ | Đang Chờ | 45.5%   |

Tiến trình Vòng 206 đang diễn ra cực kỳ bùng nổ! Kỷ lục Score mới (0.4865) đã được thiết lập ngay tại Epoch 17 với Win Rate tracking lên tới 74.5%. Mạng Neural với cấu hình dung hợp "Mắt Đại Bàng + Chu Kỳ Vàng" đang tiếp tục dò tìm điểm rơi hoàn hảo. 🚀 TheBreakthrough_206 (PID Đang Chạy) đang chờ hội tụ! Mục tiêu: 80% Win Rate!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
