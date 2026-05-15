# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_137
run_id_137 = "run_20260514_234719_v6_ASIAN_15m_TP5_SL25_BigBrain_137"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_137, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_87 = asian_res["win_rates"][3] * 100
wr_75 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 137 (BigBrain_137):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** SỰ TRÔI DẠT (DRIFTING)! Quá trình làm mịn bề mặt ở Epoch 42 đã gây ra một hiện tượng trôi dạt nhẹ. Thay vì giữ chặt mốc "0 Buy" tuyệt đối như V135 và V136, mạng Nơ-ron đã vô tình trượt vào một hố nghiêng quen thuộc: Nó thu nạp lại **{total_buy} lệnh Buy** và giảm lượng Sell xuống **{total_sell} lệnh**. Sự kết hợp này mang lại Win Rate **{wr_87:.2f}%**. Đáng chú ý, đây chính xác là tọa độ mà thuật toán đã từng đi qua ở Vòng 124 và Vòng 128. Nó cho thấy 7 Buy / 48 Sell là một vệ tinh hút rất mạnh nằm ngay cạnh Tọa Độ Kim Cương.

### Ý tưởng tiếp theo (Vòng 138 - BigBrain_138):
- **Hành động:** Chạy tiếp Vòng 138. Hạ nhiệt sâu hơn: Giảm Learning Rate về `1.5e-5` và siết Dropout xuống `0.20`.
- **Mục tiêu:** Việc mạng Nơ-ron trôi dạt sang vệ tinh (7 Buy / 48 Sell) chứng tỏ nhiệt độ (Learning Rate và Dropout) vẫn còn hơi cao, tạo ra quá nhiều rung lắc. Bằng cách siết chặt cả LR và Dropout, chúng ta sẽ ép cỗ máy "đông đặc" lại, ngăn không cho nó trôi dạt để kéo nó trở về lõi Kim Cương (0 Buy).
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_138
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_138 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_138'
run_dir_138 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_138)
os.makedirs(run_dir_138, exist_ok=True)

# Copy config from 137 to 138 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_137, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY DEEP FREEZE THERAPY: Low LR and Low Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.5e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_138
config_path_138 = os.path.join(run_dir_138, 'config.json')

with open(config_path_138, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_138.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_138}"
config_path = r"{config_path_138}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_138.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_138).

📊 Kết quả HolyGrail_137:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 132  | 0.2782 |  33.8%  |  44.4%  |  33.3%  |
| 133  | 0.2766 |  33.5%  |  44.4%  |  33.3%  |
| 134  | 0.3913 |  41.5%  |  59.5%  |  33.3%  |
| 135  | 0.3308 |  35.2%  |  56.9%  |  33.3%  |
| 136  | 0.3105 |  31.7%  |  56.9%  |  33.3%  |
| 137  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

HIỆN TƯỢNG TRÔI DẠT (DRIFTING)! Quá trình làm mịn ở Vòng 137 đã gây ra một sự dịch chuyển nhẹ. Mạng Nơ-ron đã trượt khỏi điểm lõi 0 Buy tuyệt đối và bị hút vào một "vệ tinh" nằm ngay cạnh đó: Nó thu nạp lại {total_buy} lệnh Buy và giữ {total_sell} lệnh Sell. Sự kết hợp này kéo Win Rate pha loãng xuống mốc {wr_87:.2f}%. Điều thú vị là cấu hình này là bản sao y đúc của Vòng 124 và 128 trong quá khứ! Để ngăn chặn sự rung lắc này, tôi sẽ tiến hành Đóng Băng Sâu (Deep Freeze). 🚀 HolyGrail_138 (PID {pid}) đã kích hoạt! Mục tiêu: Hạ Learning Rate về 1.5e-5 và siết Dropout xuống 0.20 để đông đặc bộ trọng số, kéo nó về lõi Kim Cương!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
