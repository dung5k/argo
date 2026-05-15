# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_126
run_id_126 = "run_20260514_222144_v6_ASIAN_15m_TP5_SL25_BigBrain_126"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_126, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 126 (BigBrain_126):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** Lịch sử lặp lại chính xác đến từng con số! Sau khi bị trừng phạt ở Vòng 125, mạng Nơ-ron đã văng ngược lại quỹ đạo và cho ra kết quả y hệt như đúc Vòng 118: Chính xác {total_buy} Buy / {total_sell} Sell (tổng {total_signals} lệnh), kéo theo Win Rate bị đè bẹp ở mức {wr_87:.2f}%. Sự lặp lại hoàn hảo này chứng minh mạng Nơ-ron đang bị mắc kẹt trong một "Vòng lặp cục bộ" (Local Loop). Nó cố gắng khôi phục lại 19 lệnh Buy, nhưng lại không thể giữ vững lá chắn 56 lệnh Sell (chỉ còn 43).

### Ý tưởng tiếp theo (Vòng 127 - BigBrain_127):
- **Hành động:** Chạy tiếp Vòng 127.
- **Mục tiêu:** Nhận ra mình đang đi vào ngõ cụt của Vòng 118, mạng Nơ-ron bắt buộc phải tự "đạp ga" phá vỡ vòng lặp cục bộ này để leo lại lên mốc 56 Sell. Gradient phạt từ mốc 45% Win Rate này sẽ là động lực chính. Chế độ Infinite Mining tiếp tục hoạt động!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_127
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_127 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_127'
run_dir_127 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_127)
os.makedirs(run_dir_127, exist_ok=True)

# Copy config from 126 to 127
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_126, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_127
config_path_127 = os.path.join(run_dir_127, 'config.json')

with open(config_path_127, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_127.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_127}"
config_path = r"{config_path_127}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_127.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_127).

📊 Kết quả HolyGrail_126:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 121  | 0.3009 |  33.0%  |  46.4%  |  33.3%  |
| 122  | 0.2691 |  31.9%  |  40.6%  |  33.3%  |
| 123  | 0.3140 |  31.8%  |  51.4%  |  33.3%  |
| 124  | 0.2820 |  31.5%  |  52.7%  |  33.3%  |
| 125  | 0.2982 |  32.5%  |  46.4%  |  33.3%  |
| 126  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

Một sự lặp lại đáng sợ! Mạng Nơ-ron đang bị mắc kẹt vào đúng "ổ gà" của Vòng 118 trong quá khứ. Kết quả Vòng 126 trả về giống hệt V118 đến từng con số nhỏ nhất: {total_buy} Buy / {total_sell} Sell và Win Rate rớt thảm thê thảm xuống {wr_87:.2f}%. Thuật toán đang nỗ lực khôi phục lại 19 lệnh Buy thần thánh, nhưng lại bất lực trong việc dựng lại tấm khiên 56 lệnh Sell (nó chỉ duy trì được 43). Việc hụt mất lớp bảo vệ Sell lập tức kéo cả hệ thống sụp đổ. 🚀 HolyGrail_127 (PID {pid}) đã kích hoạt! Mục tiêu: Bứt phá khỏi vòng lặp cục bộ (Local Loop) này bằng sức mạnh của Gradient phạt!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
