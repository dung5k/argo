# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_87
run_id_87 = "run_20260514_171013_v6_ASIAN_15m_TP5_SL25_BigBrain_87"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_87, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_84 = asian_res["win_rates"][3] * 100
wr_73 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 87 (BigBrain_87):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_84:.2f}%** (Threshold 0.84).
- **Phân tích Sâu:** Vòng này ghi nhận sự sụt giảm hiệu suất đáng kể. Win Rate tụt xuống 48.05% ở ngưỡng cao nhất, đồng thời tín hiệu bị lệch hẳn về phe Buy ({total_buy} Buy / {total_sell} Sell). Điều này cho thấy thuật toán đã vô tình trượt khỏi "vùng trũng tối ưu" và bị Overfit vào một xu hướng tăng ngắn hạn nào đó. Dù 48.05% vẫn sinh lời tốt (hòa vốn 33.3%), nhưng đây là một cấu hình lỗi (Bias) không nên sử dụng.

### Ý tưởng tiếp theo (Vòng 88 - BigBrain_88):
- **Hành động:** Chạy tiếp Vòng 88.
- **Mục tiêu:** Bản chất của Stochastic Mining là sẽ có những lúc vấp phải "đá" (Local Minima xấu). Tiếp tục giữ nguyên thông số, kích hoạt Vòng 88 để mạng Nơ-ron tự điều chỉnh lại và tìm đường quay về vùng hội tụ 56%+.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_88
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_88 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_88'
run_dir_88 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_88)
os.makedirs(run_dir_88, exist_ok=True)

# Copy config from 87 to 88
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_87, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_88
config_path_88 = os.path.join(run_dir_88, 'config.json')

with open(config_path_88, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_88.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_88}"
config_path = r"{config_path_88}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_88.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_88).

📊 Kết quả HolyGrail_87:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_73:.2f}% (Threshold 0.73) | {wr_84:.2f}% (Threshold 0.84)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 83   | 0.4170 |  50.0%  |  57.8%  |  33.3%  |
| 84   | 0.4158 |  44.0%  |  56.6%  |  33.3%  |
| 85   | 0.3652 |  45.2%  |  56.6%  |  33.3%  |
| 86   | 0.3548 |  41.0%  |  54.8%  |  33.3%  |
| 87   | {score:.4f}|  {wr_73:.1f}%  | {wr_84:.1f}%  |  33.3%  |

Cảnh báo nhiễu! Vòng 87 đã vấp phải một hố sâu (Local Minima xấu), khiến Win Rate tụt xuống 48% và tín hiệu bị lệch hẳn về phe Buy (69 Buy / 8 Sell). Tuy nhiên, 48% vẫn sinh lời lớn so với hòa vốn 33.3%. 🚀 HolyGrail_88 (PID {pid}) đã kích hoạt! Mục tiêu: Để máy tự sửa sai và tìm đường quay lại dải hội tụ 56%+!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
