# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_154
run_id_154 = "run_20260515_020359_v6_ASIAN_15m_TP5_SL25_BigBrain_154"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_154, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 154 (BigBrain_154):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_91:.2f}%** (Threshold 0.91).
- **Phân tích Sâu:** THUNG LŨNG CHẾT GIỮA HAI ĐỈNH ĐỒI! Sự vi chỉnh Learning Rate từ 1.2e-4 xuống 1.1e-4 đã hé lộ một cấu trúc kỳ lạ của vùng Loss Landscape này.
  + Ở `1.0e-4`: Trạng thái tốt (7 Buy, 51.11% WR).
  + Ở `1.2e-4`: Trạng thái tinh khiết (0 Buy, 50.00% WR).
  + Nhưng ngay chính giữa ở `1.1e-4`: Mạng lưới lại rơi vào một thung lũng chứa tới **{total_buy} lệnh Buy rác**, kéo Win Rate tụt xuống **{wr_91:.2f}%**.
- Kết luận đanh thép: Không thể lùi LR xuống dưới 1.2e-4, nếu không sẽ rơi thẳng vào thung lũng 12 Buy này! Để mở rộng thanh khoản từ mốc 0 Buy của V153, ta buộc phải tiến lên phía trước thay vì lùi lại.

### Ý tưởng tiếp theo (Vòng 155 - BigBrain_155):
- **Hành động:** Chạy tiếp Vòng 155. Kích hoạt Bước Tiến Vi Mô (Micro-Step Upward): Giữ nguyên `Dropout 0.20` và nhích nhẹ Learning Rate lên `1.3e-4`.
- **Mục tiêu:** LR 1.2e-4 đã đưa ta đến ranh giới tinh khiết 0 Buy. Nếu ta lùi (1.1e-4) thì rơi xuống hố. Vậy ta phải tiến lên! LR 1.3e-4 là bước chân cẩn trọng tiến sâu hơn vào lãnh địa Sell tuyệt đối. Kỳ vọng lực đẩy này sẽ tìm thấy các cụm tín hiệu Sell chất lượng cao nằm sâu bên trong đồi Sell, giúp kích Win Rate vượt mốc 55% mà không chạm tới ngưỡng Đảo Cực (1.5e-4)!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_155
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_155 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_155'
run_dir_155 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_155)
os.makedirs(run_dir_155, exist_ok=True)

# Copy config from 154 to 155 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_154, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY MICRO-STEP UPWARD THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.3e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_155
config_path_155 = os.path.join(run_dir_155, 'config.json')

with open(config_path_155, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_155.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_155}"
config_path = r"{config_path_155}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_155.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_155).

📊 Kết quả HolyGrail_154:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_78:.2f}% (Threshold 0.78) | {wr_91:.2f}% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 149  | 0.2846 |  33.6%  |  44.0%  |  33.3%  |
| 150  | 0.2761 |  37.4%  |  44.7%  |  33.3%  |
| 151  | 0.2738 |  33.6%  |  39.7%  |  33.3%  |
| 152  | 0.3001 |  34.6%  |  43.3%  |  33.3%  |
| 153  | 0.2752 |  36.1%  |  50.0%  |  33.3%  |
| 154  | {score:.4f}|  {wr_78:.1f}%  | {wr_91:.1f}%  |  33.3%  |

THUNG LŨNG CHẾT 1.1E-4! Việc hạ cực nhẹ LR từ 1.2 xuống 1.1e-4 tưởng chừng an toàn, nhưng lại rơi ngay vào một thung lũng chứa {total_buy} lệnh Buy rác, kéo Win Rate từ mốc 50% tụt xuống {wr_91:.2f}%. Điều này chứng tỏ ta không thể LÙI lại để mở rộng tín hiệu Sell! Để giữ vững sự thuần khiết "0 Buy", ta bắt buộc phải tiến lên. 🚀 HolyGrail_155 (PID {pid}) đã kích hoạt! Mục tiêu: Bước Tiến Vi Mô (Micro-Step Upward). Giữ Dropout 0.20 và nhích LR lên 1.3e-4 để cắm sâu hơn vào sườn dốc Sell. Kỳ vọng lực đẩy này sẽ khai quật được vùng thanh khoản Sell cực lớn, đưa Win Rate bay qua mốc 55%!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
