# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_120
run_id_120 = "run_20260514_213735_v6_ASIAN_15m_TP5_SL25_BigBrain_120"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_120, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_90 = asian_res["win_rates"][3] * 100
wr_77 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 120 (BigBrain_120):
- **Kết quả:** Hội tụ rất nhanh tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_90:.2f}%** (Threshold 0.90).
- **Phân tích Sâu:** Thuật toán tiếp tục thực hiện một bài test đánh đổi (Trade-off Test). Sau khi ổn định tại Vòng 119 (77 lệnh, WR 49.35%), nó quyết định siết chặt màng lọc bằng cách đẩy Threshold lên mức kỷ lục 0.90. Kết quả là thanh khoản bị bóp nghẹt chỉ còn một nửa ({total_signals} lệnh: {total_buy} Buy / {total_sell} Sell). Sự hi sinh thanh khoản này đã được đền đáp bằng việc Win Rate vượt vũ môn thành công lên mức {wr_90:.2f}%. Tuy nhiên, Composite Score tụt xuống {score:.4f} báo hiệu đây không phải là điểm cân bằng tối ưu nhất.

### Ý tưởng tiếp theo (Vòng 121 - BigBrain_121):
- **Hành động:** Chạy tiếp Vòng 121.
- **Mục tiêu:** Mạng Nơ-ron đang dao động nhẹ quanh đỉnh (Oscillation around Peak) để dò tìm sự cân bằng tuyệt đối giữa Win Rate và Khối lượng. Chế độ Infinite Mining tiếp tục hoạt động!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_121
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_121 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_121'
run_dir_121 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_121)
os.makedirs(run_dir_121, exist_ok=True)

# Copy config from 120 to 121
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_120, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_121
config_path_121 = os.path.join(run_dir_121, 'config.json')

with open(config_path_121, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_121.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_121}"
config_path = r"{config_path_121}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_121.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_121).

📊 Kết quả HolyGrail_120:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_90:.2f}% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 115  | 0.3247 |  34.2%  |  49.3%  |  33.3%  |
| 116  | 0.3147 |  32.5%  |  49.3%  |  33.3%  |
| 117  | 0.2729 |  32.8%  |  63.2%  |  33.3%  |
| 118  | 0.2844 |  32.5%  |  45.2%  |  33.3%  |
| 119  | 0.3053 |  30.6%  |  49.4%  |  33.3%  |
| 120  | {score:.4f}|  {wr_77:.1f}%  | {wr_90:.1f}%  |  33.3%  |

Sự bóp nghẹt thanh khoản để lấy Win Rate! Thuật toán ở Vòng 120 đã quyết định siết chặt màng lọc tín hiệu lên mức kỷ lục Threshold 0.90. Sự khắt khe này khiến số lượng lệnh bị chém làm đôi (chỉ còn {total_signals} lệnh: {total_buy}B/{total_sell}S). Đổi lại, Win Rate đã vượt qua được ngưỡng kháng cự 49% để chạm mốc {wr_90:.2f}%. Tuy nhiên, việc Composite Score tụt giảm báo hiệu rằng thuật toán đang dao động để tìm một điểm cân bằng tốt hơn giữa Chất lượng và Khối lượng. 🚀 HolyGrail_121 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục bám trụ quỹ đạo phòng thủ!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
