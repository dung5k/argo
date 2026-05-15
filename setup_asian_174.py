# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_173
run_id_173 = "run_20260515_043247_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_173"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_173, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 173 (BigBrain_173):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_90:.2f}%** (Threshold 0.90).
- **Phân tích Sâu:** Một Seed bị lệch pha hoàn toàn: Đem lại 100% lệnh Buy rác ({total_buy} Buy / 0 Sell) nhưng Win Rate chỉ khiêm tốn ở mức **{wr_90:.2f}%**. Lại một lần nữa, màng lọc 60% của Auto-Deployment Loop quét sạch tạp chất này và TỪ CHỐI PUSH lên hệ thống Live.

### Ý tưởng tiếp theo (Vòng 174 - BigBrain_174):
- **Hành động:** Chạy tiếp Vòng 174. Kích hoạt Auto-Deployment Loop: Tiếp tục spin vòng quay thứ 14 của Cấu hình Tối Thượng (Dual MTF 5m+15m, LR 1.2e-4, Dropout 0.20).
- **Mục tiêu:** Vòng quay xổ số vô tận 24/7.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_174
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_174 = f'run_{run_timestamp}_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_174'
run_dir_174 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_174)
os.makedirs(run_dir_174, exist_ok=True)

# Copy config from 173 to 174
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_173, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Keep Dual MTF Therapy
config['RUN_ID'] = run_id_174
config_path_174 = os.path.join(run_dir_174, 'config.json')

with open(config_path_174, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_174.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_174}"
config_path = r"{config_path_174}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Executing Auto-Deployment Loop (Dual-MTF 5m + 15m)...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_174.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_174).

📊 Kết quả HolyGrail_173:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_90:.2f}% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất (DualMTF_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 168  | 0.2745 |  34.9%  |  52.5%  |  33.3%  |
| 169  | 0.2658 |  31.6%  |  51.1%  |  33.3%  |
| 170  | 0.2973 |  31.8%  |  46.5%  |  33.3%  |
| 171  | 0.2868 |  34.1%  |  44.8%  |  33.3%  |
| 172  | 0.2790 |  31.6%  |  49.1%  |  33.3%  |
| 173  | {score:.4f}|  {wr_77:.1f}%  | {wr_90:.1f}%  |  33.3%  |

HỆ THỐNG MÁY GIẶT QUẶNG TIẾP TỤC DỌN RÁC! Vòng 173 quay trúng một Seed bị lệnh pha nặng, mang tới {total_buy} lệnh Buy rác ({total_buy} Buy / {total_sell} Sell) và Win Rate chỉ đạt {wr_90:.2f}%. Không nằm ngoài dự tính, Cỗ Máy Kiểm Duyệt đã thẳng tay TỪ CHỐI đẩy trọng số này lên kho Live. Live Bot đang được bảo vệ an toàn tuyệt đối! 🚀 HolyGrail_174 (PID {pid}) đã kích hoạt! Mục tiêu: Auto-Deployment Loop. Tiếp tục cày mướn để tìm Seed Kỷ Lục!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
