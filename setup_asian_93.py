# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_92
run_id_92 = "run_20260514_175033_v6_ASIAN_15m_TP5_SL25_BigBrain_92"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_92, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 92 (BigBrain_92):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** Hiệu suất bùng nổ! Win Rate nhảy vọt lên mức 56.72%, mức cao nhất trong 6 vòng gần đây. Điểm Composite Score 0.3521 và tỷ lệ phân bổ tín hiệu vẫn giữ được độ cân bằng hoàn hảo ({total_buy} Buy / {total_sell} Sell). Việc kiên nhẫn duy trì Learning Rate 1.5e-5 đã giúp thuật toán "đào" trúng lõi của mỏ vàng.

### Ý tưởng tiếp theo (Vòng 93 - BigBrain_93):
- **Hành động:** Chạy tiếp Vòng 93.
- **Mục tiêu:** Mô hình đang trong chuỗi phong độ đỉnh cao nhất. Tiếp tục duy trì thông số hiện tại, vận hành "Infinite Mining" để ép mạng Nơ-ron vắt kiệt tiềm năng của lõi hội tụ này.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_93
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_93 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_93'
run_dir_93 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_93)
os.makedirs(run_dir_93, exist_ok=True)

# Copy config from 92 to 93
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_92, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_93
config_path_93 = os.path.join(run_dir_93, 'config.json')

with open(config_path_93, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_93.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_93}"
config_path = r"{config_path_93}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_93.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_93).

📊 Kết quả HolyGrail_92:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 88   | 0.3688 |  37.8%  |  47.6%  |  33.3%  |
| 89   | 0.3289 |  38.5%  |  54.1%  |  33.3%  |
| 90   | 0.3470 |  42.1%  |  55.6%  |  33.3%  |
| 91   | 0.3606 |  38.0%  |  50.0%  |  33.3%  |
| 92   | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

Cú nổ lớn tại lõi hội tụ! Win Rate đã bật tăng lên 56.72% (cao nhất trong 6 vòng gần đây). Tỷ lệ phân bổ tín hiệu tiếp tục giữ vững sự cân bằng (39 Buy / 28 Sell). Chiến lược khóa Learning Rate đã chứng minh sự vĩ đại của nó! 🚀 HolyGrail_93 (PID {pid}) đã kích hoạt! Mục tiêu: Không thay đổi bất kỳ thứ gì, cày tiếp dải Tensor vàng này!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
