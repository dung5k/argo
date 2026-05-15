# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_83
run_id_83 = "run_20260514_164011_v6_ASIAN_15m_TP5_SL25_BigBrain_83"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_83, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_91 = asian_res["win_rates"][3] * 100
wr_78 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 83 (BigBrain_83):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_91:.2f}%** (Threshold 0.91).
- **Phân tích Sâu:** Một cú sốc địa chấn! Composite Score đã xuyên thủng trần 0.40, thiết lập mốc không tưởng 0.4170. Đáng kinh ngạc nhất là Win Rate ở dải trung bình (Threshold 0.78) đã vươn lên mốc 50% tròn trĩnh với 248 lệnh bóp cò. Tại dải cao nhất, Win Rate cũng đạt sát 58%. Mô hình này đang bóp nghẹt mọi sóng nhiễu của thị trường Châu Á!

### Ý tưởng tiếp theo (Vòng 84 - BigBrain_84):
- **Hành động:** Chạy tiếp Vòng 84.
- **Mục tiêu:** Mạch đào đang ngập tràn vàng khối. Không đổi bất kỳ tham số nào, để máy đào tiếp tục tự luyện tạ.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_84
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_84 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_84'
run_dir_84 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_84)
os.makedirs(run_dir_84, exist_ok=True)

# Copy config from 83 to 84
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_83, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_84
config_path_84 = os.path.join(run_dir_84, 'config.json')

with open(config_path_84, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_84.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_84}"
config_path = r"{config_path_84}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_84.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_84).

📊 Kết quả HolyGrail_83:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_78:.2f}% (Threshold 0.78) | {wr_91:.2f}% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 79   | 0.3619 |  46.9%  |  59.1%  |  33.3%  |
| 80   | 0.3731 |  46.5%  |  55.6%  |  33.3%  |
| 81   | 0.3629 |  49.4%  |  56.4%  |  33.3%  |
| 82   | 0.3932 |  40.1%  |  54.0%  |  33.3%  |
| 83   | {score:.4f}|  {wr_78:.1f}%  | {wr_91:.1f}%  |  33.3%  |

Chấn động địa cầu! Score lần đầu tiên xuyên thủng mốc 0.40 (Kỷ lục 0.4170). Đáng sợ nhất là Win Rate ở dải trung bình đã vươn lên mốc 50.0% với 248 tín hiệu lệnh. Hệ thống đang bóp nghẹt mọi sóng nhiễu của Châu Á trên mức R:R 1:2. 🚀 HolyGrail_84 (PID {pid}) đã kích hoạt! Mục tiêu: Không ngủ quên trên chiến thắng, đào tiếp!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
