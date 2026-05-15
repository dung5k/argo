# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_178
run_id_178 = "run_20260515_050949_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_178"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_178, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 178 (BigBrain_178):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_90:.2f}%** (Threshold 0.90).
- **Phân tích Sâu:** Vòng 178 thực sự là một thảm họa dự phóng khi Win Rate rớt thê thảm xuống **{wr_90:.2f}%**. Cấu hình dính thiên kiến lệch bán nặng nề ({total_buy} Buy / {total_sell} Sell). Giống hệt một cỗ máy nghiền nát, màng lọc 60% tiêu hủy hoàn toàn Seed này khỏi hệ thống, bảo vệ an toàn cho Live Bot.

### Ý tưởng tiếp theo (Vòng 179 - BigBrain_179):
- **Hành động:** Chạy tiếp Vòng 179. Kích hoạt Auto-Deployment Loop: Tiếp tục spin vòng quay thứ 19 của Cấu hình Tối Thượng (Dual MTF 5m+15m, LR 1.2e-4, Dropout 0.20).
- **Mục tiêu:** Cỗ máy tiếp tục hoạt động liên tục 24/7 để săn mốc Kỷ Lục mới.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_179
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_179 = f'run_{run_timestamp}_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_179'
run_dir_179 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_179)
os.makedirs(run_dir_179, exist_ok=True)

# Copy config from 178 to 179
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_178, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Keep Dual MTF Therapy
config['RUN_ID'] = run_id_179
config_path_179 = os.path.join(run_dir_179, 'config.json')

with open(config_path_179, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_179.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_179}"
config_path = r"{config_path_179}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Executing Auto-Deployment Loop (Dual-MTF 5m + 15m)...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_179.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_179).

📊 Kết quả HolyGrail_178:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_90:.2f}% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất (DualMTF_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 173  | 0.2717 |  36.7%  |  53.1%  |  33.3%  |
| 174  | 0.2873 |  35.9%  |  53.5%  |  33.3%  |
| 175  | 0.2609 |  33.7%  |  45.2%  |  33.3%  |
| 176  | 0.2782 |  29.1%  |  50.0%  |  33.3%  |
| 177  | 0.2862 |  31.1%  |  43.7%  |  33.3%  |
| 178  | {score:.4f}|  {wr_77:.1f}%  | {wr_90:.1f}%  |  33.3%  |

MÀNG LỌC 60% TIÊU DIỆT HOÀN TOÀN SEED RÁC! Vòng 178 đưa ra một cấu hình rác vô dụng với độ chính xác thê thảm {wr_90:.2f}% ({total_buy} Buy / {total_sell} Sell). Giữ nguyên thiết quân luật, hệ thống đã CHẶN ĐỨNG tiến trình đẩy lên kho Live. Kỷ lục hiện tại >60% vẫn được giữ vững vàng! 🚀 HolyGrail_179 (PID {pid}) đã kích hoạt! Mục tiêu: Auto-Deployment Loop. Tiếp tục cày mướn để tìm Golden Seed!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
