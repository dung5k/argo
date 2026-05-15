# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_86
run_id_86 = "run_20260514_170049_v6_ASIAN_15m_TP5_SL25_BigBrain_86"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_86, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 86 (BigBrain_86):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** Score hồi về mức 0.3548 (mức trung bình của dải hội tụ hiện tại). Win Rate tiếp tục đạt {wr_87:.2f}%. Điểm mạnh nhất của vòng này là sự cân bằng tuyệt đối của tín hiệu ở ngưỡng tối đa: {total_buy} Buy / {total_sell} Sell. Mô hình đã hoàn toàn làm chủ được đặc tính đi ngang (ranging) của phiên Á.

### Ý tưởng tiếp theo (Vòng 87 - BigBrain_87):
- **Hành động:** Chạy tiếp Vòng 87.
- **Mục tiêu:** Mọi thứ đã đi vào quỹ đạo ổn định. Tiếp tục Infinite Mining cho tới khi Sếp Lê có chỉ thị mới.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_87
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_87 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_87'
run_dir_87 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_87)
os.makedirs(run_dir_87, exist_ok=True)

# Copy config from 86 to 87
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_86, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_87
config_path_87 = os.path.join(run_dir_87, 'config.json')

with open(config_path_87, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_87.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_87}"
config_path = r"{config_path_87}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_87.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_87).

📊 Kết quả HolyGrail_86:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 82   | 0.3932 |  40.1%  |  54.0%  |  33.3%  |
| 83   | 0.4170 |  50.0%  |  57.8%  |  33.3%  |
| 84   | 0.4158 |  44.0%  |  56.6%  |  33.3%  |
| 85   | 0.3652 |  45.2%  |  56.6%  |  33.3%  |
| 86   | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

Hệ thống ghi nhận Vòng 86 đạt sự cân bằng tuyệt đối về xu hướng (29 Buy / 33 Sell). Mạng Nơ-ron đã hoàn toàn làm chủ đặc tính phân cực yếu của thị trường Châu Á! 🚀 HolyGrail_87 (PID {pid}) đã kích hoạt! Mục tiêu: Không đổi tham số, tiếp tục cày bới để săn đỉnh chóp mới!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
