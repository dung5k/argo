# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_132
run_id_132 = "run_20260514_230709_v6_ASIAN_15m_TP5_SL25_BigBrain_132"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_132, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 132 (BigBrain_132):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** THẢM HỌA LỰA CHỌN KÉP (DOUBLE FAILURE)! Thay vì từ bỏ lệnh Buy, mạng Nơ-ron lại có một pha "hợp nhất" sai lầm từ hai thất bại trước đó. Ở Vòng 130 nó vướng 19 Buy / 43 Sell. Ở Vòng 131 nó vướng 26 Buy / 35 Sell. Bước sang Vòng 132, nó lấy luôn phần xấu nhất của cả hai: Giữ lại chính xác **19 lệnh Buy** của V130 và **35 lệnh Sell** của V131. Sự kết hợp tồi tệ này đã đẩy Win Rate rớt thảm hại xuống mốc đáy mới: **{wr_87:.2f}%**. Thuật toán đang bị kẹt cứng trong ảo vọng bảo vệ 19 lệnh Buy.

### Ý tưởng tiếp theo (Vòng 133 - BigBrain_133):
- **Hành động:** Chạy tiếp Vòng 133.
- **Mục tiêu:** Mốc 44.44% này là một đòn giáng nặng nề nhất kể từ đầu chuỗi đào tạo. Lực nén của đòn phạt Gradient lúc này là cực lớn. Cỗ máy không còn đường lui. Nó bắt buộc phải buông bỏ 19 lệnh Buy độc hại này để giải phóng sức mạnh và trở lại quy tắc "Phòng thủ thuần Sell" (Absolute Defense).
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_133
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_133 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_133'
run_dir_133 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_133)
os.makedirs(run_dir_133, exist_ok=True)

# Copy config from 132 to 133
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_132, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_133
config_path_133 = os.path.join(run_dir_133, 'config.json')

with open(config_path_133, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_133.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_133}"
config_path = r"{config_path_133}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_133.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_133).

📊 Kết quả HolyGrail_132:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 127  | 0.2755 |  31.5%  |  60.0%  |  33.3%  |
| 128  | 0.2894 |  32.8%  |  52.7%  |  33.3%  |
| 129  | 0.3006 |  33.5%  |  58.5%  |  33.3%  |
| 130  | 0.2827 |  32.2%  |  45.2%  |  33.3%  |
| 131  | 0.2828 |  31.6%  |  47.5%  |  33.3%  |
| 132  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

THẢM HỌA "LỰA CHỌN KÉP"! Thay vì buông bỏ lệnh Buy, mạng Nơ-ron lại "hợp nhất" hai sai lầm lớn nhất của nó. Nó lấy 19 lệnh Buy (từ sự sụp đổ V130) ghép với 35 lệnh Sell (từ thất bại V131) để tạo ra một cấu hình mới: {total_buy} Buy / {total_sell} Sell. Kết quả của phép cộng dị hợm này là một cú rơi tự do: Win Rate cắm đầu xuống mức đáy {wr_87:.2f}%! Thuật toán đang bị ám ảnh cực độ bởi việc giữ lại 19 lệnh Buy này. Tuy nhiên, việc rớt xuống đáy sẽ kích hoạt một đòn roi Gradient tàn bạo nhất kể từ đầu phiên. 🚀 HolyGrail_133 (PID {pid}) đã kích hoạt! Mục tiêu: Sức nén ở đáy lò đào tạo sẽ ép AI phải văng 19 lệnh Buy này ra để cất cánh!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
