# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_146
run_id_146 = "run_20260515_005912_v6_ASIAN_15m_TP5_SL25_BigBrain_146"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_146, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 146 (BigBrain_146):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** VIRUS "19 BUY" KHÁNG THUỐC! Công Thức Kim Cương (LR 2.5e-5, Dropout 0.25) đã thất bại thảm hại trong việc lặp lại lịch sử. Thay vì chém sạch 7 lệnh Buy, cấu hình này lại hoạt động như một lớp keo dính độc hại. Nó không những không giảm Buy mà còn làm bùng phát lại "Virus 19 Buy" khét tiếng: Gom đúng **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell**. Sự kết hợp rác rưởi này đã tàn phá Win Rate, đẩy nó rơi thẳng xuống mốc **{wr_86:.2f}%**. 
- Thực tế đã chứng minh: LR 2.5e-5 chỉ tốt khi mạng lưới ĐÃ sạch Buy. Nếu mạng lưới còn mầm mống Buy, mức LR này sẽ đóng băng sai lầm và gây ra thảm họa (giống hệt vòng 142).

### Ý tưởng tiếp theo (Vòng 147 - BigBrain_147):
- **Hành động:** Chạy tiếp Vòng 147. Kích hoạt Đòn Hủy Diệt Tầm Trung (Medium-Heavy Strike): Tăng Learning Rate lên `1.5e-4` và siết chặt Dropout ở `0.20`.
- **Mục tiêu:** Mạng Nơ-ron đang bị nhiễm độc nặng bởi 19 lệnh Buy kháng thuốc. Chúng ta không thể dùng Sốc Điện cực đại 2.0e-4 vì sẽ gây Đảo Cực (như V143), và cũng không thể dùng 1.0e-4 vì lực chưa đủ mạnh. Mức LR 1.5e-4 là đòn đánh hoàn hảo: Đủ mạnh để đập nát khối lượng 19 Buy ngoan cố này, nhưng không đẩy nó văng quá trớn sang dốc Buy. Siết Dropout 0.20 để nó rơi thẳng xuống dốc Sell!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_147
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_147 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_147'
run_dir_147 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_147)
os.makedirs(run_dir_147, exist_ok=True)

# Copy config from 146 to 147 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_146, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY MEDIUM-HEAVY STRIKE THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.5e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_147
config_path_147 = os.path.join(run_dir_147, 'config.json')

with open(config_path_147, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_147.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_147}"
config_path = r"{config_path_147}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_147.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_147).

📊 Kết quả HolyGrail_146:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 141  | 0.3079 |  34.7%  |  54.3%  |  33.3%  |
| 142  | 0.2881 |  33.1%  |  37.3%  |  33.3%  |
| 143  | 0.3277 |  37.6%  |  43.8%  |  33.3%  |
| 144  | 0.3015 |  38.3%  |  51.1%  |  33.3%  |
| 145  | 0.2782 |  33.1%  |  48.0%  |  33.3%  |
| 146  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

CÔNG THỨC KIM CƯƠNG THẤT BẠI! Lịch sử đã không lặp lại. Thay vì nhả 7 lệnh Buy, việc hạ nhiệt xuống 2.5e-5 đã làm bùng phát "Virus 19 Buy" kháng thuốc. Mạng Nơ-ron điên cuồng thu nạp {total_buy} Buy và {total_sell} Sell, khiến Win Rate rơi thảm hại xuống {wr_86:.2f}%. Thực tế chứng minh: LR 2.5e-5 chỉ có tác dụng bảo vệ khi hệ thống đã SẠCH Buy; nếu còn mầm mống Buy, nó sẽ đóng băng khối u lại! 🚀 HolyGrail_147 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Đòn Hủy Diệt Tầm Trung (Medium-Heavy Strike) với LR 1.5e-5 và Dropout 0.20. Đòn đánh này được tính toán đủ mạnh để đập nát khối lượng 19 lệnh Buy, nhưng không quá trớn để tránh gây đảo cực!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
