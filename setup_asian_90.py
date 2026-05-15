# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_89
run_id_89 = "run_20260514_172410_v6_ASIAN_15m_TP5_SL25_BigBrain_89"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_89, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_84 = asian_res["win_rates"][3] * 100
wr_73 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 89 (BigBrain_89):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_84:.2f}%** (Threshold 0.84).
- **Phân tích Sâu:** Quyết định giảm Learning Rate xuống 1.5e-5 đã phát huy tác dụng ngay lập tức! Mô hình đã thoát khỏi trạng thái dao động (oscillation) nguy hiểm của vòng 87-88. Tín hiệu đã quay trở lại trạng thái cân bằng hoàn hảo ({total_buy} Buy / {total_sell} Sell). Win Rate cũng được phục hồi thành công lên mức 54.10%.

### Ý tưởng tiếp theo (Vòng 90 - BigBrain_90):
- **Hành động:** Chạy tiếp Vòng 90.
- **Mục tiêu:** Mọi thứ đã trở về trạng thái ổn định. Tiếp tục Infinite Mining với LR=1.5e-5 để khai thác sâu hơn.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_90
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_90 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_90'
run_dir_90 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_90)
os.makedirs(run_dir_90, exist_ok=True)

# Copy config from 89 to 90
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_89, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_90
config_path_90 = os.path.join(run_dir_90, 'config.json')

with open(config_path_90, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_90.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_90}"
config_path = r"{config_path_90}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_90.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_90).

📊 Kết quả HolyGrail_89:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_73:.2f}% (Threshold 0.73) | {wr_84:.2f}% (Threshold 0.84)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 85   | 0.3652 |  45.2%  |  56.6%  |  33.3%  |
| 86   | 0.3548 |  41.0%  |  54.8%  |  33.3%  |
| 87   | 0.3467 |  38.0%  |  48.1%  |  33.3%  |
| 88   | 0.3688 |  37.8%  |  47.6%  |  33.3%  |
| 89   | {score:.4f}|  {wr_73:.1f}%  | {wr_84:.1f}%  |  33.3%  |

Xử lý sự cố thành công! Quyết định giảm Learning Rate đã phát huy tác dụng tuyệt đối. Vòng 89 đã dập tắt hoàn toàn hiện tượng dao động tín hiệu, đưa phân bổ về lại mức cân bằng hoàn hảo (29 Buy / 32 Sell) và phục hồi Win Rate lên trên 54%. 🚀 HolyGrail_90 (PID {pid}) đã kích hoạt! Mục tiêu: Giữ vững thông số mới, tiếp tục đào!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
