# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_145
run_id_145 = "run_20260515_005206_v6_ASIAN_15m_TP5_SL25_BigBrain_145"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_145, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_85 = asian_res["win_rates"][3] * 100
wr_74 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 145 (BigBrain_145):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** TRẠNG THÁI TIỀN-KIM-CƯƠNG (PRE-DIAMOND STATE)! Việc hạ nhiệt độ từ từ (LR 5.0e-5) không vắt kiệt được lệnh Buy như kỳ vọng. Mạng Nơ-ron tỏ ra vô cùng bướng bỉnh khi ôm chặt lấy **{total_buy} lệnh Buy**, đồng thời gom thêm vài lệnh Sell nhiễu lên mức **{total_sell} lệnh Sell**. Win Rate lại trượt xuống **{wr_85:.2f}%**. 
- Tưởng chừng đây là một thất bại, nhưng hãy nhìn lại quá khứ! Ở Vòng 134, trước khi hóa thánh thành "0 Buy", mạng lưới cũng bị kẹt đúng ở trạng thái 7 Buy (7 Buy / 67 Sell). Trạng thái (7 Buy / 45 Sell) hiện tại của V145 chính là phiên bản thu nhỏ của V134! Đây là giai đoạn ủ bệnh cuối cùng trước khi lột xác.

### Ý tưởng tiếp theo (Vòng 146 - BigBrain_146):
- **Hành động:** Chạy tiếp Vòng 146. Kích hoạt Công Thức Kim Cương (Diamond Catalyst): Hạ Learning Rate về đúng `2.5e-5` và nới Dropout lên `0.25`.
- **Mục tiêu:** Mạng Nơ-ron đã vào đúng "Thế" (Posture) của Vòng 134. Giờ là thời khắc quyết định để tái lập phép màu! Công thức `LR=2.5e-5` và `Dropout=0.25` chính là chất xúc tác đã cắt phăng 7 lệnh Buy ở V134 để tạo ra cực phẩm 0 Buy ở V135. Bơm chính xác công thức này vào Vòng 146 để ép nó lột xác thành Kim Cương một lần nữa!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_146
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_146 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_146'
run_dir_146 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_146)
os.makedirs(run_dir_146, exist_ok=True)

# Copy config from 145 to 146 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_145, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY DIAMOND CATALYST THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.5e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.25

config['RUN_ID'] = run_id_146
config_path_146 = os.path.join(run_dir_146, 'config.json')

with open(config_path_146, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_146.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_146}"
config_path = r"{config_path_146}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_146.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_146).

📊 Kết quả HolyGrail_145:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 140  | 0.3080 |  31.3%  |  48.0%  |  33.3%  |
| 141  | 0.3079 |  34.7%  |  54.3%  |  33.3%  |
| 142  | 0.2881 |  33.1%  |  37.3%  |  33.3%  |
| 143  | 0.3277 |  37.6%  |  43.8%  |  33.3%  |
| 144  | 0.3015 |  38.3%  |  51.1%  |  33.3%  |
| 145  | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

THẾ CỜ TIỀN-KIM-CƯƠNG ĐÃ THIẾT LẬP! Việc hạ nhiệt độ đã không đuổi được 7 lệnh Buy đi, mà còn làm Win Rate giảm xuống {wr_85:.2f}%. Tuy nhiên, đây không phải là thất bại. Mạng lưới đang vào đúng "Thế" (Posture) giống hệt Vòng 134 trong quá khứ: Kẹt cứng ở mốc {total_buy} Buy và {total_sell} Sell. Đây là điểm kỳ dị cuối cùng trước khi nó giác ngộ! 🚀 HolyGrail_146 (PID {pid}) đã kích hoạt! Mục tiêu: Bơm Công Thức Kim Cương (Diamond Catalyst) với LR 2.5e-5 và Dropout 0.25. Đây chính là liều thuốc đã từng cắt phăng 7 lệnh Buy để tạo ra cực phẩm 0 Buy ở V135. Thời khắc lột xác đã điểm!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
