import subprocess, sys

msg = """🏯 [ASIAN V6 MTF] Đang Chờ (HolyGrail_204).

📊 Kết quả HolyGrail_203:
- Best Val Loss tại Epoch 12. Composite Score: 0.4843
- Win Rate: 64.70% (Threshold 0.77) | 74.07% (Threshold 0.89)

📈 Bảng tổng kết 6 vòng gần nhất (Scale Up D_MODEL=64):
| Vòng | Score  | WR@0.77 | WR@0.89 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 199  | 0.2208 | 32.20%  | N/A     | 45.5%   |
| 200  | LỖI    | N/A     | N/A     | 45.5%   |
| 201  | 0.2230 | 40.82%  | N/A     | 45.5%   |
| 202  | 0.4723 | 62.65%  | 68.96%  | 45.5%   |
| 203  | 0.4843 | 64.70%  | 74.07%  | 45.5%   |
| 204  | Đang Chờ | Đang Chờ | Đang Chờ | 45.5%   |

Tiến trình huấn luyện Vòng 204 (Holy Grail Scaling với D_MODEL=64, BATCH=512) đang diễn ra mượt mà và chưa có dấu hiệu Overfit (Early Stopping chưa kích hoạt). Hệ thống tiếp tục nới lỏng thời gian để não bộ tiêu hóa khối lượng dữ liệu khổng lồ từ 3 đồng coin. 🚀 HolyGrail_204 (PID Đang Chạy) đang chờ hội tụ! Mục tiêu: Bứt phá mốc 80% Win Rate!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
subprocess.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
