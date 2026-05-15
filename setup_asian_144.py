# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_143
run_id_143 = "run_20260515_003459_v6_ASIAN_15m_TP5_SL25_BigBrain_143"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_143, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_80 = asian_res["win_rates"][3] * 100
wr_71 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 143 (BigBrain_143):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_80:.2f}%** (Threshold 0.80).
- **Phân tích Sâu:** SỐC ĐIỆN ĐẢO CỰC (POLARITY FLIP)! Liều Sốc Điện cực mạnh (LR 2.0e-4) đã thành công nổ tung cái bẫy 37% Win Rate. Tuy nhiên, lực nổ quá mạnh đã ném mạng Nơ-ron văng tít sang sườn dốc bên kia của thung lũng. Kết quả là nó bị "Đảo cực": Từ chỗ kẹt 56 lệnh Sell ở vòng trước, giờ nó lật ngược thành **{total_buy} lệnh Buy** và chỉ có **{total_sell} lệnh Sell**. Do phiên Á vốn rất kỵ lệnh Buy, sự áp đảo của phe Buy này khiến Win Rate chỉ hồi phục lửng lơ ở mức **{wr_80:.2f}%**. Mạng lưới đã thoát chết nhưng lại hạ cánh sai sườn dốc.

### Ý tưởng tiếp theo (Vòng 144 - BigBrain_144):
- **Hành động:** Chạy tiếp Vòng 144. Kích hoạt Đòn Đánh Chiến Thuật (Calculated Strike): Chỉnh Learning Rate về `1.0e-4` và siết Dropout xuống `0.20`.
- **Mục tiêu:** Sốc Điện 2.0e-4 là quá bạo liệt và gây ra Đảo cực. Giờ chúng ta cần một cú đấm vừa đủ (1.0e-4) để đẩy mạng lưới từ sườn dốc nghiêng Buy lăn trở về sườn dốc nghiêng Sell (nơi có tỷ lệ Win Rate > 50%). Đồng thời, siết Dropout xuống 0.20 để giảm độ nảy, ép nó nhanh chóng neo lại vào các vách đá an toàn (như tỷ lệ 1:1 hoặc 1:2 đã từng xuất hiện).
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_144
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_144 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_144'
run_dir_144 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_144)
os.makedirs(run_dir_144, exist_ok=True)

# Copy config from 143 to 144 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_143, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY CALCULATED STRIKE THERAPY: Strong LR and Low Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_144
config_path_144 = os.path.join(run_dir_144, 'config.json')

with open(config_path_144, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_144.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_144}"
config_path = r"{config_path_144}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_144.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_144).

📊 Kết quả HolyGrail_143:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_71:.2f}% (Threshold 0.71) | {wr_80:.2f}% (Threshold 0.80)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 138  | 0.2824 |  38.5%  |  56.7%  |  33.3%  |
| 139  | 0.3327 |  32.6%  |  53.8%  |  33.3%  |
| 140  | 0.3080 |  31.3%  |  48.0%  |  33.3%  |
| 141  | 0.3079 |  34.7%  |  54.3%  |  33.3%  |
| 142  | 0.2881 |  33.1%  |  37.3%  |  33.3%  |
| 143  | {score:.4f}|  {wr_71:.1f}%  | {wr_80:.1f}%  |  33.3%  |

SỐC ĐIỆN GÂY ĐẢO CỰC (POLARITY FLIP)! Liều Sốc Điện 2.0e-4 đã nổ tung cái bẫy 37% Win Rate, cứu mạng Nơ-ron khỏi cái chết lâm sàng. TUY NHIÊN, lực nổ là quá mạnh khiến nó văng tít sang sườn dốc bên kia của thung lũng. Từ chỗ bị áp đảo bởi lệnh Sell, giờ nó lật ngược 180 độ thành một cấu hình thiên vị Buy: {total_buy} lệnh Buy và chỉ {total_sell} lệnh Sell. Do phiên Á rất kỵ lệnh Buy, Win Rate chỉ có thể ngóc lên được {wr_80:.2f}%. 🚀 HolyGrail_144 (PID {pid}) đã kích hoạt! Mục tiêu: Tung một Đòn Đánh Chiến Thuật (Calculated Strike) với LR 1.0e-4 để đẩy mạng Nơ-ron lăn trở về sườn dốc nghiêng Sell, và siết Dropout 0.20 để ép nó neo lại vùng Win Rate > 50%!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
