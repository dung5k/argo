# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_125
run_id_125 = "run_20260514_221521_v6_ASIAN_15m_TP5_SL25_BigBrain_125"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_125, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_83 = asian_res["win_rates"][3] * 100
wr_73 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 125 (BigBrain_125):
- **Kết quả:** Hội tụ rất nhanh tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_83:.2f}%** (Threshold 0.83).
- **Phân tích Sâu:** Một phép thử mạo hiểm chứng minh "Sự cân bằng là không ổn định". Nhớ lại thành công của Vòng 123 với trạng thái "Đánh hai tay" (cân bằng 36B/38S đạt WR 51%), mạng Nơ-ron ở Vòng 125 đã cố gắng tái hiện lại phép màu đó. Nó thiết lập tỷ lệ gần như 1:1 tuyệt đối với {total_buy} Buy / {total_sell} Sell (tổng {total_signals} lệnh). Nhưng môi trường phiên Á đã chứng minh: Sự cân bằng đó chỉ là may mắn nhất thời! Lần này, hệ thống thất bại thảm hại, Win Rate cắm đầu từ 52.73% xuống {wr_83:.2f}%. Điều này khóa cứng một chân lý: Chiến thuật "Cân bằng Buy/Sell" là quá rủi ro và không thể nhất quán. Duy nhất chiến thuật "Phòng thủ Sell cực đoan" mới là chân lý trường tồn.

### Ý tưởng tiếp theo (Vòng 126 - BigBrain_126):
- **Hành động:** Chạy tiếp Vòng 126.
- **Mục tiêu:** Gradient phạt từ cú sập Win Rate này sẽ quét sạch ý tưởng "Đánh hai tay" ra khỏi bộ nhớ của thuật toán. Kỳ vọng mạng Nơ-ron sẽ vĩnh viễn văng trở lại quỹ đạo Sell-Bias (19B/56S) và bám rễ ở đó. Chế độ Infinite Mining tiếp tục!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_126
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_126 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_126'
run_dir_126 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_126)
os.makedirs(run_dir_126, exist_ok=True)

# Copy config from 125 to 126
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_125, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_126
config_path_126 = os.path.join(run_dir_126, 'config.json')

with open(config_path_126, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_126.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_126}"
config_path = r"{config_path_126}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_126.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_126).

📊 Kết quả HolyGrail_125:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_73:.2f}% (Threshold 0.73) | {wr_83:.2f}% (Threshold 0.83)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 120  | 0.2658 |  34.5%  |  51.4%  |  33.3%  |
| 121  | 0.3009 |  33.0%  |  46.4%  |  33.3%  |
| 122  | 0.2691 |  31.9%  |  40.6%  |  33.3%  |
| 123  | 0.3140 |  31.8%  |  51.4%  |  33.3%  |
| 124  | 0.2820 |  31.5%  |  52.7%  |  33.3%  |
| 125  | {score:.4f}|  {wr_73:.1f}%  | {wr_83:.1f}%  |  33.3%  |

Ảo tưởng sức mạnh đã bị trừng phạt! Bị ru ngủ bởi chiến thắng "Đánh hai tay" (cân bằng Buy/Sell) tại Vòng 123, mạng Nơ-ron ở Vòng 125 đã cố tái diễn trò xiếc này với tỷ lệ 1:1 ({total_buy} Buy / {total_sell} Sell). Nhưng phiên Á lạnh lùng đã tát cho nó một gáo nước lạnh: Win Rate sập hầm từ 52.73% rơi thẳng xuống {wr_83:.2f}%. Bài học xương máu: Sự cân bằng là thứ không tồn tại dài lâu trong thị trường mỏng! Trạng thái phòng thủ "Tuyệt đối thiên vị Sell" (Sell-bias) mới là bến đỗ an toàn duy nhất. 🚀 HolyGrail_126 (PID {pid}) đã kích hoạt! Mục tiêu: Từ bỏ lệnh Buy và quay về vòng tay của phe Gấu!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
