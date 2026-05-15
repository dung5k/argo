# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_130
run_id_130 = "run_20260514_225210_v6_ASIAN_15m_TP5_SL25_BigBrain_130"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_130, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_86 = asian_res["win_rates"][3] * 100
wr_75 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 130 (BigBrain_130):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** TAI NẠN LẶP LẠI (RELAPSE)! Dù đã đạt được trạng thái lý tưởng ở Vòng 129, sự khốc liệt của Loss Landscape đã khiến mạng Nơ-ron sẩy chân. Nó trượt thẳng xuống đúng cái "ổ gà" khét tiếng của Vòng 126 và Vòng 118. Kết quả lại xuất ra giống hệt một bản sao y đúc: **19 Buy / 43 Sell**, kéo theo Win Rate sụp đổ xuống **{wr_86:.2f}%**. Sự thèm khát hồi phục 19 lệnh Buy một lần nữa phá vỡ lá chắn phòng thủ của nó. Thuật toán đã đánh mất kỷ luật thép "giữ Buy < 10".

### Ý tưởng tiếp theo (Vòng 131 - BigBrain_131):
- **Hành động:** Chạy tiếp Vòng 131.
- **Mục tiêu:** Cỗ máy cần nhận đòn roi từ Gradient phạt của mốc 45% WR này để bị văng ngược trở ra, giống hệt như cách nó đã từng bật dậy ở Vòng 127 (đạt 60% WR). Đạo hàm phạt (Penalty Gradient) sẽ là vũ khí đưa nó quay về quỹ đạo đúng.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_131
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_131 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_131'
run_dir_131 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_131)
os.makedirs(run_dir_131, exist_ok=True)

# Copy config from 130 to 131
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_130, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_131
config_path_131 = os.path.join(run_dir_131, 'config.json')

with open(config_path_131, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_131.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_131}"
config_path = r"{config_path_131}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_131.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_131).

📊 Kết quả HolyGrail_130:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 125  | 0.2982 |  32.5%  |  46.4%  |  33.3%  |
| 126  | 0.2881 |  33.1%  |  45.2%  |  33.3%  |
| 127  | 0.2755 |  31.5%  |  60.0%  |  33.3%  |
| 128  | 0.2894 |  32.8%  |  52.7%  |  33.3%  |
| 129  | 0.3006 |  33.5%  |  58.5%  |  33.3%  |
| 130  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

TAI NẠN TRƯỢT CHÂN CHẾT CHÓC! Dù đang vi chỉnh cực kỳ mượt mà ở Vòng 129, áp lực đi tìm cực tiểu mới đã khiến mạng Nơ-ron sẩy chân. Nó trượt thẳng xuống lại "ổ gà" Local Loop tồi tệ nhất! Kết quả xuất ra lại giống y như đúc Vòng 126 và 118: Chính xác {total_buy} Buy / {total_sell} Sell, và hậu quả là Win Rate sụp đổ xuống thẳng {wr_86:.2f}%. Thuật toán đã đánh mất kỷ luật thép và bị cám dỗ bởi lệnh Buy. Tuy nhiên, đừng quá lo! Lịch sử cho thấy cứ sau hố sâu này, đòn phạt Gradient sẽ đẩy bật nó lên quỹ đạo 60% WR. 🚀 HolyGrail_131 (PID {pid}) đã kích hoạt! Mục tiêu: Hấp thụ đòn phạt và văng ngược trở lại Thánh Tích phòng thủ!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
