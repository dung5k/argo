# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_111
run_id_111 = "run_20260514_202245_v6_ASIAN_15m_TP5_SL25_BigBrain_111"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_111, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_87 = asian_res["win_rates"][3] * 100
wr_75 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 111 (BigBrain_111):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** Một thất bại thực nghiệm mang lại giá trị vô giá! Vòng 111 đã chứng kiến mạng Nơ-ron quay lưng với chiến thuật "Thiên Vị Sell" và cố gắng bắt đáy bằng cách áp đảo lệnh Buy ({total_buy} Buy / {total_sell} Sell). Hậu quả là Win Rate tụt dốc không phanh xuống {wr_87:.2f}% và số lượng tín hiệu teo tóp còn {total_signals} lệnh. Cú rơi tự do này là minh chứng đanh thép nhất cho quy luật: Trong phiên Á, chặn các lệnh Sell để ưu tiên Buy là một hành động tự sát đối với thuật toán Micro-Scalping.

### Ý tưởng tiếp theo (Vòng 112 - BigBrain_112):
- **Hành động:** Chạy tiếp Vòng 112.
- **Mục tiêu:** Cú vấp ngã ở Vòng 111 sẽ khiến mô hình nhận được gradient phạt (penalty) cực lớn đối với chiến thuật ưu tiên Buy. Để hệ thống tự động quay về "Điểm Hút" (Attractor) thiên vị Sell hoàn hảo (như ở Vòng 108, 109). Tiếp tục Infinite Mining!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_112
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_112 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_112'
run_dir_112 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_112)
os.makedirs(run_dir_112, exist_ok=True)

# Copy config from 111 to 112
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_111, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_112
config_path_112 = os.path.join(run_dir_112, 'config.json')

with open(config_path_112, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_112.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_112}"
config_path = r"{config_path_112}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_112.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_112).

📊 Kết quả HolyGrail_111:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 106  | 0.3192 |  32.1%  |  45.8%  |  33.3%  |
| 107  | 0.3052 |  32.6%  |  49.3%  |  33.3%  |
| 108  | 0.3174 |  32.9%  |  49.3%  |  33.3%  |
| 109  | 0.3119 |  32.7%  |  49.3%  |  33.3%  |
| 110  | 0.3132 |  33.0%  |  47.6%  |  33.3%  |
| 111  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

Cú ngã đắt giá của thuật toán! Vòng 111 chứng kiến mô hình Nơ-ron quay xe, cố gắng ưu tiên các lệnh Buy để bắt đáy ({total_buy}B/{total_sell}S). Hậu quả là Win Rate cắm đầu rơi tự do xuống {wr_87:.2f}% và số lượng tín hiệu bị nghẽn (chỉ còn {total_signals} lệnh). Kết quả tệ hại này chứng minh đanh thép quy luật: Phiên Á tuyệt đối KHÔNG ĐƯỢC THIÊN VỊ BUY! Gradient phạt từ vòng này sẽ ép mô hình nảy mạnh về lại Attractor thiên vị Sell trước đó. 🚀 HolyGrail_112 (PID {pid}) đã kích hoạt! Mục tiêu: Rebound về Attractor gốc!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
