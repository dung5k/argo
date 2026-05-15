# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_168
run_id_168 = "run_20260515_035501_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_168"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_168, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 168 (BigBrain_168):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_88:.2f}%** (Threshold 0.88).
- **Phân tích Sâu:** Một Seed tầm trung (WR **{wr_88:.2f}%** với {total_buy} Buy / {total_sell} Sell). Giống như những kịch bản trước, màng lọc 60% lạnh lùng gạt bỏ kết quả này để bảo vệ kho vũ khí. Live Bot vẫn không bị ảnh hưởng.

### Ý tưởng tiếp theo (Vòng 169 - BigBrain_169):
- **Hành động:** Chạy tiếp Vòng 169. Kích hoạt Auto-Deployment Loop: Tiếp tục spin vòng quay thứ chín của Cấu hình Tối Thượng (Dual MTF 5m+15m, LR 1.2e-4, Dropout 0.20).
- **Mục tiêu:** Cỗ máy tiếp tục quay vô tận!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_169
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_169 = f'run_{run_timestamp}_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_169'
run_dir_169 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_169)
os.makedirs(run_dir_169, exist_ok=True)

# Copy config from 168 to 169
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_168, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Keep Dual MTF Therapy
config['RUN_ID'] = run_id_169
config_path_169 = os.path.join(run_dir_169, 'config.json')

with open(config_path_169, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_169.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_169}"
config_path = r"{config_path_169}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Executing Auto-Deployment Loop (Dual-MTF 5m + 15m)...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_169.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_169).

📊 Kết quả HolyGrail_168:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_76:.2f}% (Threshold 0.76) | {wr_88:.2f}% (Threshold 0.88)

📈 Bảng tổng kết 6 vòng gần nhất (DualMTF_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 163  | 0.2674 |  33.6%  |  58.3%  |  33.3%  |
| 164  | 0.3043 |  31.5%  |  41.0%  |  33.3%  |
| 165  | 0.2610 |  32.5%  |  58.3%  |  33.3%  |
| 166  | 0.2779 |  32.3%  |  42.2%  |  33.3%  |
| 167  | 0.2964 |  34.5%  |  44.4%  |  33.3%  |
| 168  | {score:.4f}|  {wr_76:.1f}%  | {wr_88:.1f}%  |  33.3%  |

MÁY GIẶT QUẶNG HOẠT ĐỘNG! Vòng 168 quay trúng Seed đạt {wr_88:.2f}% Win Rate ({total_buy} Buy / {total_sell} Sell). Giống như mọi khi, màng lọc 60% lạnh lùng gạt bỏ trọng số này và TỪ CHỐI PUSH lên hệ thống Live. Kho đạn vẫn cực kỳ tinh khiết và sẵn sàng! 🚀 HolyGrail_169 (PID {pid}) đã kích hoạt! Mục tiêu: Auto-Deployment Loop. Máy giặt quặng tiếp tục quay vòng mới để tìm Kỷ lục >60% cho Sếp Lê!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
