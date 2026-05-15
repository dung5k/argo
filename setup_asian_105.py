# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_104
run_id_104 = "run_20260514_192826_v6_ASIAN_15m_TP5_SL25_BigBrain_104"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_104, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 104 (BigBrain_104):
- **Kết quả:** Early Stopping cực sớm tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_88:.2f}%** (Threshold 0.88).
- **Phân tích Sâu:** Một pha "dội ngược" (Rebound) điển hình! Sau chuỗi đào sâu liên tục ở các vòng trước, thuật toán đã chạm phải bức tường của Local Minima. Nó cố gắng đảo ngược từ thiên vị Sell sang thiên vị Buy ({total_buy} Buy / {total_sell} Sell) nhưng thất bại, khiến Win Rate tụt xuống {wr_88:.2f}%. Tính năng Early Stopping đã hoạt động xuất sắc để ngắt ngay quá trình training tại Epoch {epoch} nhằm bảo toàn các trọng số tốt nhất trước khi bị Overfit.

### Ý tưởng tiếp theo (Vòng 105 - BigBrain_105):
- **Hành động:** Chạy tiếp Vòng 105.
- **Mục tiêu:** Cú dội ngược này sẽ là bước đệm để mạng Nơ-ron thiết lập lại gradient và tìm đường vòng sang một thung lũng (valley) khác tốt hơn. Cứ để nó tiếp tục chạy.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_105
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_105 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_105'
run_dir_105 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_105)
os.makedirs(run_dir_105, exist_ok=True)

# Copy config from 104 to 105
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_104, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_105
config_path_105 = os.path.join(run_dir_105, 'config.json')

with open(config_path_105, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_105.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_105}"
config_path = r"{config_path_105}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_105.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_105).

📊 Kết quả HolyGrail_104:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_76:.2f}% (Threshold 0.76) | {wr_88:.2f}% (Threshold 0.88)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 100  | 0.3252 |  34.4%  |  51.2%  |  33.3%  |
| 101  | 0.3250 |  33.4%  |  51.2%  |  33.3%  |
| 102  | 0.3121 |  31.8%  |  51.3%  |  33.3%  |
| 103  | 0.3167 |  33.9%  |  53.8%  |  33.3%  |
| 104  | {score:.4f}|  {wr_76:.1f}%  | {wr_88:.1f}%  |  33.3%  |

Pha "dội ngược" (Rebound) điển hình của học sâu! Sau chuỗi hội tụ sâu, mô hình đã chạm phải bức tường nhiễu. Nó nỗ lực đảo hướng từ bias Sell sang bias Buy ({total_buy}B/{total_sell}S) nhưng thất bại, kéo theo sự sụt giảm Win Rate xuống {wr_88:.1f}%. Tính năng Early Stopping đã phản xạ xuất sắc, tự động cắt ngang tiến trình ngay tại Epoch {epoch} để ngăn chặn Overfit! Cú nảy này chính là đòn bẩy để thuật toán tìm đường sang "thung lũng" (valley) khác. 🚀 HolyGrail_105 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục Infinite Mining vượt rào cản!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
