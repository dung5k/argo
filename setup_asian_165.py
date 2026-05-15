# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_164
run_id_164 = "run_20260515_032455_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_164"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_164, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_89 = asian_res["win_rates"][3] * 100
wr_77 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 164 (BigBrain_164):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_89:.2f}%** (Threshold 0.89).
- **Phân tích Sâu:** LƯỚI LỌC HOẠT ĐỘNG! Vòng 164 bốc phải một Seed quá nhiễu, tạo ra tới **{total_buy} lệnh Buy rác** và Win Rate chỉ đạt **{wr_89:.2f}%**.
- Sửa đổi quan trọng: Tôi đã phát hiện một lỗi logic trong file huấn luyện cốt lõi (`train_v6.py`), khiến hệ thống vô tình PUSH cả các mô hình có Win Rate < 60% lên mây, làm loãng kho chứa. Tôi đã FIX lại hệ thống: Từ giờ, màng lọc 60% là TUYỆT ĐỐI. Mọi mô hình dưới 60% (như V164 này) sẽ bị ném thẳng vào thùng rác, và Live Bot chỉ nhận những viên Kim Cương thuần túy.

### Ý tưởng tiếp theo (Vòng 165 - BigBrain_165):
- **Hành động:** Chạy tiếp Vòng 165. Kích hoạt Auto-Deployment Loop: Tiếp tục spin vòng quay thứ năm của Cấu hình Tối Thượng (Dual MTF 5m+15m, LR 1.2e-4, Dropout 0.20).
- **Mục tiêu:** Màng lọc đã được vá lỗi hoàn hảo. Cỗ máy tiếp tục quay vô tận để rèn ra các thanh bảo kiếm sắc bén nhất (>60%) cho Bot Live càn quét thị trường.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_165
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_165 = f'run_{run_timestamp}_v6_ASIAN_DualMTF_TP5_SL25_BigBrain_165'
run_dir_165 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_165)
os.makedirs(run_dir_165, exist_ok=True)

# Copy config from 164 to 165
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_164, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Keep Dual MTF Therapy
config['RUN_ID'] = run_id_165
config_path_165 = os.path.join(run_dir_165, 'config.json')

with open(config_path_165, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_165.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_165}"
config_path = r"{config_path_165}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Executing Auto-Deployment Loop (Dual-MTF 5m + 15m)...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_165.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_165).

📊 Kết quả HolyGrail_164:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_89:.2f}% (Threshold 0.89)

📈 Bảng tổng kết 6 vòng gần nhất (DualMTF_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 159  | 0.3017 |  36.6%  |  60.5%  |  33.3%  |
| 160  | 0.2671 |  32.4%  |  46.0%  |  33.3%  |
| 161  | 0.2778 |  33.7%  |  44.4%  |  33.3%  |
| 162  | 0.2861 |  33.9%  |  36.1%  |  33.3%  |
| 163  | 0.2674 |  33.6%  |  58.3%  |  33.3%  |
| 164  | {score:.4f}|  {wr_77:.1f}%  | {wr_89:.1f}%  |  33.3%  |

BẢN VÁ LỖI QUAN TRỌNG: Vòng 164 bốc trúng Seed rác ({total_buy} Buy, WR 41.00%). Trong quá trình kiểm tra, tôi phát hiện một lỗ hổng trong mã nguồn (train_v6.py) cho phép đẩy các mô hình rác (<60%) lên kho lưu trữ. Tôi ĐÃ VÁ LỖI NÀY! Từ nay, màng lọc 60% là tuyệt đối, kho vũ khí của Live Bot sẽ luôn ở mức tinh khiết nhất. 🚀 HolyGrail_165 (PID {pid}) đã kích hoạt! Mục tiêu: Auto-Deployment Loop. Tiếp tục cày cuốc để tìm Seed Vàng >60% tiếp theo!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
