# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_151
run_id_151 = "run_20260515_014039_v6_ASIAN_15m_TP5_SL25_BigBrain_151"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_151, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 151 (BigBrain_151):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** SỤP ĐỔ VÁCH ĐÁ! Chiến thuật Giãn Nở (LR 2.5e-5) đã thất bại thảm hại và phá hủy hoàn toàn thành quả "0 Buy" của Vòng 150. Việc hạ LR đã làm mất đi "lực đẩy" cần thiết, khiến mạng lưới lập tức trượt chân ngã ngược lại vào Thung lũng Buy. Nó nhặt phải **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell** (tỷ lệ 1:1 rác rưởi). Win Rate sập hầm xuống **{wr_85:.2f}%**.
- Bài học cốt tử: Điểm "0 Buy" ở V150 KHÔNG phải là một bình nguyên ổn định, mà là một VÁCH ĐÁ. Nếu ta không duy trì lực đẩy liên tục bằng LR 1.0e-4, mạng lưới sẽ rơi tự do xuống vực. Chốt hạ: Không bao giờ được hạ LR dưới 1.0e-4 ở khu vực này!

### Ý tưởng tiếp theo (Vòng 152 - BigBrain_152):
- **Hành động:** Chạy tiếp Vòng 152. Kích hoạt Đòn Cân Bằng Vàng (Golden Middle Strike): Cố định cứng Learning Rate ở `1.0e-4` và vi chỉnh Dropout về chính giữa: `0.15`.
- **Mục tiêu:** Chúng ta đã biết: 
  + LR 1.0e-4 + Dropout 0.20 = 51.1% WR nhưng lọt 7 Buy (V144).
  + LR 1.0e-4 + Dropout 0.10 = 44.7% WR và 0 Buy (V150).
  Vậy Dropout 0.20 có độ nhiễu đủ tốt để tìm ra Sell xịn (kéo WR lên), nhưng lại để lọt rác Buy. Dropout 0.10 chặn đứng mọi rác Buy, nhưng lại quá gắt khiến thuật toán không gắp được Sell xịn.
  Mức Dropout `0.15` chính là Điểm Cân Bằng Vàng lý thuyết: Đủ nhiễu để tìm kiếm Sell chất lượng cao (kéo WR > 50%), nhưng đủ gắt để đập chết mọi mầm mống Buy!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_152
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_152 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_152'
run_dir_152 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_152)
os.makedirs(run_dir_152, exist_ok=True)

# Copy config from 151 to 152 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_151, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY GOLDEN MIDDLE STRIKE THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.15

config['RUN_ID'] = run_id_152
config_path_152 = os.path.join(run_dir_152, 'config.json')

with open(config_path_152, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_152.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_152}"
config_path = r"{config_path_152}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_152.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_152).

📊 Kết quả HolyGrail_151:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 146  | 0.2898 |  34.0%  |  39.1%  |  33.3%  |
| 147  | 0.2858 |  34.0%  |  51.9%  |  33.3%  |
| 148  | 0.2906 |  36.5%  |  37.7%  |  33.3%  |
| 149  | 0.2846 |  33.6%  |  44.0%  |  33.3%  |
| 150  | 0.2761 |  37.4%  |  44.7%  |  33.3%  |
| 151  | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

SỤP ĐỔ VÁCH ĐÁ! Vòng 151 chứng minh tọa độ "0 Buy" của V150 không phải vùng an toàn mà là một Vách Đá. Khi ta ngắt "lực đẩy" bằng cách hạ LR xuống 2.5e-5, thuật toán lập tức trượt chân rơi thẳng xuống vực sâu của Thung lũng Buy. Nó nhặt phải {total_buy} lệnh Buy và {total_sell} lệnh Sell (tỷ lệ 1:1 tồi tệ nhất), dìm Win Rate xuống {wr_85:.2f}%. Kết luận sắt đá: Phải luôn duy trì lực đẩy LR 1.0e-4 để không bị rơi xuống vực! 🚀 HolyGrail_152 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Đòn Cân Bằng Vàng (Golden Middle Strike) với LR 1.0e-4 (duy trì lực đẩy) và Dropout 0.15 (Điểm cân bằng lý thuyết giữa 0.20 và 0.10). Kỳ vọng nhặt được Sell xịn của 0.20 và chém sạch Buy rác của 0.10!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
