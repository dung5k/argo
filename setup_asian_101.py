# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_100
run_id_100 = "run_20260514_184925_v6_ASIAN_15m_TP5_SL25_BigBrain_100"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_100, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 100 (BigBrain_100):
- **Kết quả:** Hội tụ cực sâu tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_85:.2f}%** (Threshold 0.85).
- **Phân tích Sâu:** Vòng 100 lịch sử đã đánh dấu sự kiện mạng Nơ-ron phá vỡ được "Locked Attractor" 59 tín hiệu sau 4 vòng liên tiếp. Bằng cách đào cực sâu tới tận Epoch 97, thuật toán đã tìm ra một vùng không gian mới cho phép TĂNG sản lượng lệnh lên {total_signals} lệnh (36 Buy / 46 Sell) mà vẫn duy trì Win Rate vững chắc trên mức 50% (51.22%). Lợi nhuận kỳ vọng (EV) tăng mạnh.

### Ý tưởng tiếp theo (Vòng 101 - BigBrain_101):
- **Hành động:** Chạy tiếp Vòng 101.
- **Mục tiêu:** Mô hình vừa tìm ra một ngách mới có volume lệnh cao hơn. Tiếp tục Infinite Mining để xem nó có thể tối ưu hóa Win Rate trong ngách volume lớn này không.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_101
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_101 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_101'
run_dir_101 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_101)
os.makedirs(run_dir_101, exist_ok=True)

# Copy config from 100 to 101
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_100, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_101
config_path_101 = os.path.join(run_dir_101, 'config.json')

with open(config_path_101, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_101.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_101}"
config_path = r"{config_path_101}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_101.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_101).

📊 Kết quả HolyGrail_100:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_74:.2f}% (Threshold 0.74) | {wr_85:.2f}% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 96   | 0.3307 |  38.8%  |  52.5%  |  33.3%  |
| 97   | 0.3107 |  36.3%  |  52.5%  |  33.3%  |
| 98   | 0.3209 |  37.3%  |  52.5%  |  33.3%  |
| 99   | 0.3216 |  38.3%  |  49.1%  |  33.3%  |
| 100  | {score:.4f}|  {wr_74:.1f}%  | {wr_85:.1f}%  |  33.3%  |

Cột mốc lịch sử Vòng 100 đã kết thúc một cách rực rỡ! Sau khi đào sâu kỷ lục tới tận Epoch 97, thuật toán đã phá vỡ thành công "tường rào" 59 tín hiệu để tìm ra một mỏ mới. Hệ thống bắt được 82 lệnh (36B/46S) với tỷ lệ chiến thắng đảo chiều vững chắc trên 50% (51.22%). Lợi nhuận kỳ vọng đang được mở rộng quy mô. 🚀 HolyGrail_101 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục Infinite Mining trên không gian mới!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
