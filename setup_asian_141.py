# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_140
run_id_140 = "run_20260515_001038_v6_ASIAN_15m_TP5_SL25_BigBrain_140"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_140, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 140 (BigBrain_140):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** LÕI ĐỐI XỨNG VỠ VỤN! Cú sốc nhẹ từ Dropout `0.25` ở vòng trước đã tạo ra sự bành trướng tuyệt đẹp, nhưng hóa ra "Lõi Đối Xứng 1:1" lại cực kỳ mỏng manh. Khi tiếp tục đào sâu thêm một vòng (Epoch 16), thuật toán đã không giữ được thăng bằng. Nó bị trượt khỏi điểm đối xứng 39/39 và rớt thẳng xuống cái hố quen thuộc: Thu nạp lại **{total_buy} lệnh Buy** và tung ra **{total_sell} lệnh Sell**. Sự phá vỡ đối xứng này ngay lập tức kéo Win Rate lao dốc xuống mốc **{wr_85:.2f}%**. Sự mong manh này chứng tỏ bề mặt quanh lõi đối xứng rất dốc.

### Ý tưởng tiếp theo (Vòng 141 - BigBrain_141):
- **Hành động:** Chạy tiếp Vòng 141. Kích hoạt Cú Hích Vừa (Moderate Kick): Tăng Learning Rate lên `5.0e-5` và siết Dropout xuống `0.20`.
- **Mục tiêu:** Mạng Nơ-ron lại rơi vào bẫy 48% Win Rate. Chúng ta cần một "cú hích" để ném nó ra khỏi hố này. Việc tăng LR lên 5.0e-5 sẽ cấp đủ năng lượng để hất văng nó, trong khi Dropout 0.20 sẽ giới hạn sự tò mò để nó không bay quá xa khỏi dải 50%+ Win Rate.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_141
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_141 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_141'
run_dir_141 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_141)
os.makedirs(run_dir_141, exist_ok=True)

# Copy config from 140 to 141 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_140, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY MODERATE KICK THERAPY: Med LR and Low Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 5.0e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_141
config_path_141 = os.path.join(run_dir_141, 'config.json')

with open(config_path_141, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_141.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_141}"
config_path = r"{config_path_141}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_141.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_141).

📊 Kết quả HolyGrail_140:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 135  | 0.3308 |  35.2%  |  56.9%  |  33.3%  |
| 136  | 0.3105 |  31.7%  |  56.9%  |  33.3%  |
| 137  | 0.2974 |  34.1%  |  52.7%  |  33.3%  |
| 138  | 0.2824 |  38.5%  |  56.7%  |  33.3%  |
| 139  | 0.3327 |  32.6%  |  53.8%  |  33.3%  |
| 140  | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

KIỆT TÁC ĐỐI XỨNG BỊ PHÁ VỠ! "Lõi Đối Xứng 1:1" tuyệt đẹp ở Vòng 139 đã chứng tỏ sự mỏng manh của nó. Khi đào sâu thêm (Infinite Mining), mạng Nơ-ron đã mất thăng bằng và trượt khỏi đỉnh đối xứng này. Nó rơi tóm vào cái hố {total_buy} Buy / {total_sell} Sell quen thuộc. Sự sụp đổ tỷ lệ vàng này ngay lập tức kéo Win Rate cắm đầu từ 53.85% xuống còn {wr_85:.2f}%. Sự trôi dạt này là hệ quả tất yếu do Gradient không thể bám víu vào sườn dốc trơn trượt của Lõi Kim Cương. 🚀 HolyGrail_141 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Cú Hích (LR 5.0e-5) để ném mạng Nơ-ron văng ra khỏi cái hố 48% này, đồng thời siết Dropout (0.20) để ép nó đi tìm một bình nguyên an toàn hơn!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
