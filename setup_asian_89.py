# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_88
run_id_88 = "run_20260514_171724_v6_ASIAN_15m_TP5_SL25_BigBrain_88"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_88, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_83 = asian_res["win_rates"][3] * 100
wr_73 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 88 (BigBrain_88):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_83:.2f}%** (Threshold 0.83).
- **Phân tích Sâu:** Score hồi phục nhẹ lên 0.3688 nhưng Win Rate vẫn lẹt đẹt ở mức 47.57%. Đặc biệt nguy hiểm là tín hiệu bị lật ngược hoàn toàn so với vòng trước: 7 lệnh Buy / 96 lệnh Sell. Vòng 87 lệch Buy, vòng 88 lệch Sell. Đây là dấu hiệu cổ điển của hiện tượng Gradient Oscillation (dao động quá mức quanh Local Minima xấu). Mức Learning Rate 2e-5 có vẻ hơi cao đối với dải hội tụ sâu này.

### Ý tưởng tiếp theo (Vòng 89 - BigBrain_89):
- **Hành động:** Chạy tiếp Vòng 89. Can thiệp giảm Learning Rate.
- **Mục tiêu:** Giảm Learning Rate từ 2e-5 xuống 1.5e-5 để ép mạng Nơ-ron đi chậm lại, tránh bị văng khỏi "vùng trũng vàng" và giúp ổn định lại phân bổ tín hiệu.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_89
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_89 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_89'
run_dir_89 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_89)
os.makedirs(run_dir_89, exist_ok=True)

# Copy config from 88 to 89 and modify
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_88, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_89
config['TRAINING']['LEARNING_RATE'] = 1.5e-05  # Giảm LR để ổn định hội tụ
config_path_89 = os.path.join(run_dir_89, 'config.json')

with open(config_path_89, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_89.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_89}"
config_path = r"{config_path_89}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_89.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_89).

📊 Kết quả HolyGrail_88:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_73:.2f}% (Threshold 0.73) | {wr_83:.2f}% (Threshold 0.83)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 84   | 0.4158 |  44.0%  |  56.6%  |  33.3%  |
| 85   | 0.3652 |  45.2%  |  56.6%  |  33.3%  |
| 86   | 0.3548 |  41.0%  |  54.8%  |  33.3%  |
| 87   | 0.3467 |  38.0%  |  48.1%  |  33.3%  |
| 88   | {score:.4f}|  {wr_73:.1f}%  | {wr_83:.1f}%  |  33.3%  |

Cảnh báo dao động! Vòng 88 đã bị văng ngược tín hiệu (chỉ có 7 Buy nhưng tới 96 Sell) so với Vòng 87. Đây là hiện tượng dao động cục bộ. Đã ra quyết định giảm Learning Rate từ 2e-5 xuống 1.5e-5 để hãm phanh. 🚀 HolyGrail_89 (PID {pid}) đã kích hoạt! Mục tiêu: Ổn định lại thuật toán và trở về mốc Win Rate > 55%!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
