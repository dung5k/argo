# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_144
run_id_144 = "run_20260515_004533_v6_ASIAN_15m_TP5_SL25_BigBrain_144"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_144, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 144 (BigBrain_144):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** ĐÒN ĐÁNH CHIẾN THUẬT THÀNH CÔNG! Lực đẩy tinh toán (LR 1.0e-4) đã hoạt động hoàn hảo. Nó đã lăn khối trọng số từ sườn dốc nghiêng Buy (bị kẹt 47 lệnh Buy ở V143) lăn ngược trở lại sườn dốc nghiêng Sell quen thuộc. Kết quả là mạng lưới rũ bỏ được phần lớn lệnh Buy, chỉ còn giữ lại **{total_buy} lệnh Buy** và tung ra **{total_sell} lệnh Sell**. Do trở về đúng địa hình phòng thủ của phiên Á, Win Rate đã bật tăng trở lại mốc an toàn **{wr_86:.2f}%**. Sự xuất hiện của cấu hình 7 Buy này một lần nữa khẳng định đây là một vệ tinh rất mạnh xoay quanh Tọa độ Kim Cương.

### Ý tưởng tiếp theo (Vòng 145 - BigBrain_145):
- **Hành động:** Chạy tiếp Vòng 145. Kích hoạt Hạ Nhiệt Chậm (Slow Cooldown): Giảm Learning Rate xuống `5.0e-5` và giữ nguyên Dropout `0.20`.
- **Mục tiêu:** Mạng Nơ-ron đã hạ cánh an toàn trên sườn dốc Sell (Win Rate > 50%). Giờ là lúc từ từ làm nguội để nó trượt dọc theo sườn dốc này xuống vùng lõi. Bằng cách dùng LR 5.0e-5, chúng ta kỳ vọng nó sẽ dần dần nhả nốt 7 lệnh Buy cuối cùng ra để tái lập mức Win Rate 56%+ như thời kỳ hoàng kim V135!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_145
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_145 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_145'
run_dir_145 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_145)
os.makedirs(run_dir_145, exist_ok=True)

# Copy config from 144 to 145 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_144, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY SLOW COOLDOWN THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 5.0e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_145
config_path_145 = os.path.join(run_dir_145, 'config.json')

with open(config_path_145, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_145.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_145}"
config_path = r"{config_path_145}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_145.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_145).

📊 Kết quả HolyGrail_144:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 139  | 0.3327 |  32.6%  |  53.8%  |  33.3%  |
| 140  | 0.3080 |  31.3%  |  48.0%  |  33.3%  |
| 141  | 0.3079 |  34.7%  |  54.3%  |  33.3%  |
| 142  | 0.2881 |  33.1%  |  37.3%  |  33.3%  |
| 143  | 0.3277 |  37.6%  |  43.8%  |  33.3%  |
| 144  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

ĐÒN ĐÁNH CHIẾN THUẬT THÀNH CÔNG! Lực đẩy tinh toán LR 1.0e-4 đã đẩy thành công khối trọng số lăn ngược trở lại sườn dốc nghiêng Sell. AI đã gột rửa được mớ lệnh Buy ồ ạt ở vòng trước, hạ cánh với một tỷ lệ quen thuộc: {total_buy} Buy và {total_sell} Sell. Việc trở về địa hình phòng thủ truyền thống của phiên Á ngay lập tức giúp Win Rate bật tăng trở lại mốc an toàn {wr_86:.2f}%. 🚀 HolyGrail_145 (PID {pid}) đã kích hoạt! Mục tiêu: Hạ nhiệt chậm (Slow Cooldown) với LR 5.0e-5 và Dropout 0.20. Cho phép AI từ từ trượt dọc theo sườn dốc Sell này xuống đáy thung lũng để vắt kiệt nốt 7 lệnh Buy cuối cùng!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
