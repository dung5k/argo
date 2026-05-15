# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_131
run_id_131 = "run_20260514_225850_v6_ASIAN_15m_TP5_SL25_BigBrain_131"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_131, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_86 = asian_res["win_rates"][3] * 100
wr_75 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 131 (BigBrain_131):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** Phản ứng dữ dội của mạng Nơ-ron dưới đòn phạt Gradient! Ở Vòng 130, nó sụp đổ ở mốc 45% do lọt 19 lệnh Buy. Thay vì sợ hãi và cắt giảm lệnh Buy như kỳ vọng, nó lại chọn cách "gồng lỗ" bằng cách... nhồi thêm lệnh Buy lên con số {total_buy}, đồng thời rút bớt lệnh Sell xuống {total_sell}. Lựa chọn "đánh hai tay" này giúp Win Rate nhích nhẹ lên mức {wr_86:.2f}%. Tuy nhiên, đây vẫn là một mức Win Rate yếu kém và ngập ngụa trong rủi ro. Thuật toán vẫn đang ngoan cố bấu víu vào các tín hiệu Buy giả mạo.

### Ý tưởng tiếp theo (Vòng 132 - BigBrain_132):
- **Hành động:** Chạy tiếp Vòng 132.
- **Mục tiêu:** Mạng Nơ-ron cần bị trừng phạt thêm một lần nữa ở mốc 47% này để nhận ra sự vô vọng của chiến lược "bắt đáy" (Buy). Chế độ Infinite Mining sẽ tiếp tục giáng đòn Loss xuống cho đến khi nó từ bỏ hoàn toàn {total_buy} lệnh Buy này để quay về bến đỗ an toàn 60% WR thuần Sell.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_132
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_132 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_132'
run_dir_132 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_132)
os.makedirs(run_dir_132, exist_ok=True)

# Copy config from 131 to 132
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_131, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_132
config_path_132 = os.path.join(run_dir_132, 'config.json')

with open(config_path_132, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_132.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_132}"
config_path = r"{config_path_132}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_132.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_132).

📊 Kết quả HolyGrail_131:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 126  | 0.2881 |  33.1%  |  45.2%  |  33.3%  |
| 127  | 0.2755 |  31.5%  |  60.0%  |  33.3%  |
| 128  | 0.2894 |  32.8%  |  52.7%  |  33.3%  |
| 129  | 0.3006 |  33.5%  |  58.5%  |  33.3%  |
| 130  | 0.2827 |  32.2%  |  45.2%  |  33.3%  |
| 131  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

CÚ VÙNG VẪY NGOAN CỐ CỦA AI! Sau tai nạn trượt chân thảm khốc xuống mốc 45% ở Vòng 130 (do lọt 19 lệnh Buy), mạng Nơ-ron phải gánh chịu đòn trừng phạt Gradient. Tuy nhiên, thay vì sợ hãi cắt lệnh Buy như Vòng 127, nó lại chọn cách "Gồng Lỗ" điên cuồng: Nhồi thêm lệnh Buy lên mức {total_buy} lệnh, và rút bớt lá chắn Sell xuống {total_sell} lệnh. Sự kết hợp chắp vá này kéo Win Rate nhích nhẹ lên {wr_86:.2f}%. Dẫu vậy, đây vẫn là một chiến thuật chứa đầy rủi ro và ảo tưởng! Nó chưa tỉnh ngộ để nhận ra lệnh Buy là kịch độc. 🚀 HolyGrail_132 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục giáng đòn phạt để ép AI đầu hàng, từ bỏ lệnh Buy và trở về chiến thuật Phòng thủ Thuần Sell!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
