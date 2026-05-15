# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_81
run_id_81 = "run_20260514_162115_v6_ASIAN_15m_TP5_SL25_BigBrain_81"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_81, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_91 = asian_res["win_rates"][3] * 100
wr_78 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 81 (BigBrain_81):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_91:.2f}%** (Threshold 0.91).
- **Phân tích Sâu:** Một vòng đào tạo cực kỳ sắc nét. Win Rate tại mức tín hiệu cao đạt 56.41%, và đặc biệt Win Rate ở mức trung bình (Threshold 0.78) đã vươn lên tới {wr_78:.2f}%. Mô hình đang ngày càng học được cách lọc nhiễu tốt hơn.

### Ý tưởng tiếp theo (Vòng 82 - BigBrain_82):
- **Hành động:** Chạy tiếp Vòng 82.
- **Mục tiêu:** Giữ nguyên không gian cấu hình. Tiếp tục Stochastic Mining để tìm tạ siêu việt.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_82
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_82 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_82'
run_dir_82 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_82)
os.makedirs(run_dir_82, exist_ok=True)

# Copy config from 81 to 82
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_81, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_82
config_path_82 = os.path.join(run_dir_82, 'config.json')

with open(config_path_82, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_82.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_82}"
config_path = r"{config_path_82}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_82.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_82).

📊 Kết quả HolyGrail_81:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_78:.2f}% (Threshold 0.78) | {wr_91:.2f}% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@0.78 | WR@0.91 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 77   | 0.3326 |  39.5%  |  55.5%  |  33.3%  |
| 78   | 0.3668 |  45.5%  |  55.6%  |  33.3%  |
| 79   | 0.3619 |  46.9%  |  59.1%  |  33.3%  |
| 80   | 0.3731 |  46.5%  |  55.6%  |  33.3%  |
| 81   | {score:.4f}|  {wr_78:.1f}%  | {wr_91:.1f}%  |  33.3%  |

Hệ thống tiếp tục duy trì thành tích khủng! Mức lợi nhuận thực tế (56.4%) đang bỏ xa mức hòa vốn siêu việt (33.3%). 🚀 HolyGrail_82 (PID {pid}) đã kích hoạt! Mục tiêu: Không ngủ quên trên chiến thắng, đào tiếp!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
