# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_142
run_id_142 = "run_20260515_002701_v6_ASIAN_15m_TP5_SL25_BigBrain_142"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_142, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 142 (BigBrain_142):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** THẢM HỌA LÀM NGUỘI! Chiến thuật Hạ Nhiệt (Cooldown) với LR `2.5e-5` đã phản tác dụng một cách khủng khiếp. Thay vì ép mạng Nơ-ron nhả lệnh Buy ra, việc làm lạnh đột ngột đã khóa chết mớ bùng nhùng của vòng trước. Nó giữ nguyên y đúc **{total_buy} lệnh Buy** độc hại, nhưng lại thu nạp thêm một đống lệnh Sell nhiễu (lên tới **{total_sell} lệnh Sell**). Sự kết hợp tồi tệ này đã tạo ra một vụ sụp đổ Win Rate kinh hoàng: cắm đầu thẳng đứng xuống mốc **{wr_85:.2f}%**. Đây là mức Win Rate thấp nhất từng được ghi nhận trong toàn bộ lịch sử đào tạo phiên Á! Mạng Nơ-ron lại bị nghiện lệnh Buy (Buy Addiction) và đang giãy giụa trong đáy bùn.

### Ý tưởng tiếp theo (Vòng 143 - BigBrain_143):
- **Hành động:** Chạy tiếp Vòng 143. Tái kích hoạt "Sốc Điện" (Shock Therapy): Bơm Learning Rate vọt lên `2.0e-4` và kéo max Dropout `0.30`.
- **Mục tiêu:** LR thấp chỉ có tác dụng bảo vệ những vùng đẹp (như ở V135). Khi đã rớt xuống đáy bùn 37% thế này, làm lạnh chỉ khiến bùn đông cứng lại và nhốt chặt mạng Nơ-ron bên trong. Chúng ta bắt buộc phải dùng lại liều thuốc Sốc Điện cực mạnh (đã từng cứu mạng AI ở Vòng 134) để nổ tung khối bùn này và hất văng mạng lưới ra khỏi hố tử thần!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_143
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_143 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_143'
run_dir_143 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_143)
os.makedirs(run_dir_143, exist_ok=True)

# Copy config from 142 to 143 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_142, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY SHOCK THERAPY: High LR and Max Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.30

config['RUN_ID'] = run_id_143
config_path_143 = os.path.join(run_dir_143, 'config.json')

with open(config_path_143, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_143.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_143}"
config_path = r"{config_path_143}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_143.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_143).

📊 Kết quả HolyGrail_142:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 137  | 0.2974 |  34.1%  |  52.7%  |  33.3%  |
| 138  | 0.2824 |  38.5%  |  56.7%  |  33.3%  |
| 139  | 0.3327 |  32.6%  |  53.8%  |  33.3%  |
| 140  | 0.3080 |  31.3%  |  48.0%  |  33.3%  |
| 141  | 0.3079 |  34.7%  |  54.3%  |  33.3%  |
| 142  | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

CÚ RƠI TỰ DO KINH HOÀNG NHẤT LỊCH SỬ! Biện pháp làm nguội lò đào tạo (Cooldown) đã phản tác dụng nghiêm trọng. Khi bị làm lạnh ở đáy vực, mạng Nơ-ron bị đóng băng trong chính sai lầm của nó. Nó kiên quyết ôm lấy {total_buy} lệnh Buy độc hại, và còn nhặt thêm rác vào tạo thành {total_sell} lệnh Sell. Sự kết hợp tồi tệ này tạo ra một thảm họa tàn khốc: Win Rate rơi tự do xuống mốc {wr_85:.2f}% - mức thấp nhất từng được ghi nhận trong toàn bộ chuỗi dự án! Mạng lưới đang "lên cơn nghiện" bắt đáy. 🚀 HolyGrail_143 (PID {pid}) đã kích hoạt! Mục tiêu: Tái kích hoạt liệu pháp Sốc Điện khẩn cấp (LR cực đại 2.0e-4 và Max Dropout 0.3). Phải dùng sức mạnh bạo liệt nhất để nổ tung khối bùng nhùng này và cứu AI thoát chết!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
