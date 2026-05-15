# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_148
run_id_148 = "run_20260515_011432_v6_ASIAN_15m_TP5_SL25_BigBrain_148"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_148, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 148 (BigBrain_148):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** ĐÒN TÌM KIẾM TRƯỢT MỤC TIÊU! Lực đẩy tinh khắc (LR 8.0e-5) đã thành công trong việc gõ mạng Nơ-ron văng khỏi tọa độ Phản-Kim-Cương (100% Buy) của vòng trước. Tuy nhiên, nó đã trượt mục tiêu "0 Buy" và rơi thẳng xuống một cái hố rác: Gom phải **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell**. Sự kết hợp hỗn loạn này đã kéo Win Rate sập thẳng đứng xuống mốc **{wr_87:.2f}%**.
- Quỹ đạo của Loss Landscape đã rõ ràng: LR 1.5e-4 văng sang 100% Buy. LR 8.0e-5 rơi xuống hố rác 37%. Điểm cân bằng duy nhất nằm ở LR 1.0e-4 (đã từng tạo ra 51.11% Win Rate ở Vòng 144).

### Ý tưởng tiếp theo (Vòng 149 - BigBrain_149):
- **Hành động:** Chạy tiếp Vòng 149. Kích hoạt Reset Cấu Trúc (Structured Reset): Đặt Learning Rate ở mức chuẩn xác `1.0e-4` và nới lỏng Dropout lên `0.25`.
- **Mục tiêu:** Chúng ta bắt buộc phải đưa mạng lưới quay trở lại tọa độ ổn định của Vòng 144 (nơi có Win Rate > 50%) để thoát khỏi mớ rác này. Bằng cách sử dụng lại `LR=1.0e-4` nhưng kết hợp với Dropout cao hơn (`0.25` thay vì `0.20`), chúng ta kỳ vọng sự nhiễu loạn thêm vào này sẽ đóng vai trò như một màng lọc, ép mạng lưới phải vứt bỏ những lệnh Buy ngoan cố ngay khi vừa chạm mặt đất, để tiến thẳng tới Tọa độ Kim Cương!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_149
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_149 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_149'
run_dir_149 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_149)
os.makedirs(run_dir_149, exist_ok=True)

# Copy config from 148 to 149 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_148, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY STRUCTURED RESET THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.25

config['RUN_ID'] = run_id_149
config_path_149 = os.path.join(run_dir_149, 'config.json')

with open(config_path_149, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_149.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_149}"
config_path = r"{config_path_149}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_149.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_149).

📊 Kết quả HolyGrail_148:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 143  | 0.3277 |  37.6%  |  43.8%  |  33.3%  |
| 144  | 0.3015 |  38.3%  |  51.1%  |  33.3%  |
| 145  | 0.2782 |  33.1%  |  48.0%  |  33.3%  |
| 146  | 0.2898 |  34.0%  |  39.1%  |  33.3%  |
| 147  | 0.2858 |  34.0%  |  51.9%  |  33.3%  |
| 148  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

CÚ ĐÁNH TRƯỢT MỤC TIÊU! Lực lượng giác tinh vi LR 8.0e-5 đã thành công gõ bật mạng Nơ-ron khỏi cực Phản-Kim-Cương (100% Buy) của vòng trước. Đáng tiếc là nó trượt mốc "0 Buy" lý tưởng và lăn thẳng xuống một hố rác chứa {total_buy} Buy và {total_sell} Sell. Kết quả tất yếu là Win Rate sập hầm xuống {wr_87:.2f}%. Dải lực tối ưu đã lộ diện: 1.5e-4 ném văng đi, 8.0e-5 rơi xuống hố. Cột mốc an toàn duy nhất là điểm 1.0e-4! 🚀 HolyGrail_149 (PID {pid}) đã kích hoạt! Mục tiêu: Reset Cấu Trúc với LR 1.0e-4 (trở về điểm tựa an toàn 51.11% của V144) nhưng tăng Dropout lên 0.25 để xóc rớt phần rác Buy cặn bã trong lúc rơi xuống!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
