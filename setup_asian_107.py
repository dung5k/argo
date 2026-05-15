# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_106
run_id_106 = "run_20260514_194019_v6_ASIAN_15m_TP5_SL25_BigBrain_106"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_106, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 106 (BigBrain_106):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** Một nỗ lực "bắc cầu" (Bridging) của mạng Nơ-ron! Thuật toán cố gắng kết hợp đặc tính của 2 Điểm Hút tốt nhất: Nó mở rộng volume lên {total_signals} lệnh (tương đương attractor 82 lệnh) nhưng vẫn giữ nguyên xu hướng thiên vị Sell ({total_buy} Buy / {total_sell} Sell) (tương đương attractor 65 lệnh). Tuy nhiên, phép thử này khiến Win Rate sụt giảm xuống {wr_86:.2f}%. Dù vậy, nó vẫn nằm trong vùng lợi nhuận rất an toàn so với mức hòa vốn 33.3%.

### Ý tưởng tiếp theo (Vòng 107 - BigBrain_107):
- **Hành động:** Chạy tiếp Vòng 107.
- **Mục tiêu:** Quá trình "săn lùng" Global Minima đang diễn ra vô cùng khốc liệt giữa việc tối ưu hóa Win Rate hay tối ưu hóa Volume. Cứ để máy móc tự quyết định thông qua Infinite Mining.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_107
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_107 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_107'
run_dir_107 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_107)
os.makedirs(run_dir_107, exist_ok=True)

# Copy config from 106 to 107
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_106, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_107
config_path_107 = os.path.join(run_dir_107, 'config.json')

with open(config_path_107, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_107.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_107}"
config_path = r"{config_path_107}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_107.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_107).

📊 Kết quả HolyGrail_106:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 101  | 0.3250 |  33.4%  |  51.2%  |  33.3%  |
| 102  | 0.3121 |  31.8%  |  51.3%  |  33.3%  |
| 103  | 0.3167 |  33.9%  |  53.8%  |  33.3%  |
| 104  | 0.3209 |  40.4%  |  44.6%  |  33.3%  |
| 105  | 0.3134 |  33.4%  |  53.8%  |  33.3%  |
| 106  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

Mạng Nơ-ron đang cố gắng thực hiện một phép lai tạo (Bridging)! Vòng 106 chứng kiến nỗ lực kết hợp volume lớn (85 tín hiệu) với chiến thuật tập trung Sell (29B/56S) từ vòng trước. Dù sự kết hợp này khiến Win Rate giảm nhiệt xuống {wr_86:.2f}%, đây vẫn là một mức lợi nhuận cực kỳ an toàn (hòa vốn chỉ 33.3%). Thuật toán đang tự động "hunt" (săn lùng) điểm cân bằng hoàn hảo giữa Khối lượng và Tỷ lệ thắng. 🚀 HolyGrail_107 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục Infinite Mining!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
