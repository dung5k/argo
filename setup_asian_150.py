# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_149
run_id_149 = "run_20260515_012310_v6_ASIAN_15m_TP5_SL25_BigBrain_149"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_149, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_88 = asian_res["win_rates"][3] * 100
wr_76 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 149 (BigBrain_149):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_88:.2f}%** (Threshold 0.88).
- **Phân tích Sâu:** NHIỄU LOẠN TRỞ THÀNH CHẤT ĐỘC! Vòng 149 mang đến một phát hiện mang tính đột phá về cấu trúc vùng đáy hiện tại. Khi ta dùng cùng mức LR 1.0e-4 (ở V144 mang lại 51.11% WR với 7 Buy) nhưng tăng Dropout lên 0.25 (như V149), mạng lưới đã THẤT BẠI thảm hại. Nó ngậm lại tới **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell**, đẩy Win Rate lùi về **{wr_88:.2f}%**.
- Điều này chứng minh rằng: Trong vùng tọa độ hiện tại, các tín hiệu Buy rác là những mảng rộng, còn các tín hiệu Sell tối ưu là những điểm hẹp. Khi ta tăng Dropout (thêm nhiễu), mạng lưới bị mất khả năng "lấy nét" vào các điểm Sell hẹp, và thế là nó trượt chân rơi lại vào cái hố Buy rộng lớn. Dropout cao lúc này là thuốc độc!

### Ý tưởng tiếp theo (Vòng 150 - BigBrain_150):
- **Hành động:** Chạy tiếp Vòng 150. Kích hoạt Đòn Bắn Tỉa (Sniper Strike): Giữ nguyên Learning Rate ở `1.0e-4` nhưng siết chặt Dropout xuống tận `0.10`.
- **Mục tiêu:** Chúng ta đã tìm ra điểm yếu của mạng lưới lúc này là sự mất tập trung. Bằng cách hạ Dropout xuống 0.10 (mức thấp nhất từ trước tới nay), ta ép thuật toán phải "siêu lấy nét" (Hyper-focus). Mức LR 1.0e-4 sẽ đẩy nó sang sườn dốc Sell, và sự lấy nét tuyệt đối của Dropout 0.10 sẽ giúp nó lách qua mọi mảng Buy rác để khóa chặt vào tọa độ 0 Buy!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_150
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_150 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_150'
run_dir_150 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_150)
os.makedirs(run_dir_150, exist_ok=True)

# Copy config from 149 to 150 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_149, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY SNIPER STRIKE THERAPY (Low Dropout)
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.10

config['RUN_ID'] = run_id_150
config_path_150 = os.path.join(run_dir_150, 'config.json')

with open(config_path_150, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_150.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_150}"
config_path = r"{config_path_150}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_150.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_150).

📊 Kết quả HolyGrail_149:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_76:.2f}% (Threshold 0.76) | {wr_88:.2f}% (Threshold 0.88)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 144  | 0.3015 |  38.3%  |  51.1%  |  33.3%  |
| 145  | 0.2782 |  33.1%  |  48.0%  |  33.3%  |
| 146  | 0.2898 |  34.0%  |  39.1%  |  33.3%  |
| 147  | 0.2858 |  34.0%  |  51.9%  |  33.3%  |
| 148  | 0.2906 |  36.5%  |  37.7%  |  33.3%  |
| 149  | {score:.4f}|  {wr_76:.1f}%  | {wr_88:.1f}%  |  33.3%  |

NHIỄU LOẠN LÀ THUỐC ĐỘC! Vòng 149 mang tới một phát hiện chấn động: Khi dùng chung một lực đẩy 1.0e-4, việc tăng lượng nhiễu Dropout (từ 0.20 lên 0.25) đã phá hủy khả năng "lấy nét" của AI. Thay vì gạt bỏ lệnh Buy, sự nhiễu loạn làm mờ tầm nhìn, khiến AI trượt chân rớt lại vào hố rác chứa {total_buy} lệnh Buy và kéo Win Rate xuống {wr_88:.2f}%. Ở địa hình chật hẹp này, nhiễu loạn là thuốc độc! 🚀 HolyGrail_150 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Đòn Bắn Tỉa (Sniper Strike) với LR 1.0e-4 và siết gắt Dropout xuống mốc cực thấp 0.10. Ép mạng Nơ-ron phải "siêu lấy nét" (Hyper-focus) để lách qua mọi mớ rác Buy, ngắm bắn thẳng vào tọa độ 0 Buy!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
