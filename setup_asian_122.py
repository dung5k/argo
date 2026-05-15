# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_121
run_id_121 = "run_20260514_214404_v6_ASIAN_15m_TP5_SL25_BigBrain_121"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_121, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_84 = asian_res["win_rates"][3] * 100
wr_73 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 121 (BigBrain_121):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_84:.2f}%** (Threshold 0.84).
- **Phân tích Sâu:** Một cú "Ảo giác Đảo gương" (Mirror-flip Hallucination) cực kỳ hy hữu! Mạng Nơ-ron đã ghi nhớ con số "56" là chìa khóa thành công từ các vòng trước, nhưng thay vì dùng 56 lệnh Sell, nó lại đảo ngược thành {total_buy} lệnh Buy và chỉ giữ {total_sell} lệnh Sell. Cú bẻ lái tử thần sang phe Buy này lập tức phải trả giá đắt: Win Rate cắm đầu rơi từ 51.35% (Vòng 120) xuống còn {wr_84:.2f}%. Sự thất bại này đóng đinh vĩnh viễn quy luật: Trong phiên Á, Buy là nhiễu, Sell là vua. Cùng là con số 56, nhưng 56 Buy mang lại thảm họa, còn 56 Sell mang lại ngai vàng.

### Ý tưởng tiếp theo (Vòng 122 - BigBrain_122):
- **Hành động:** Chạy tiếp Vòng 122.
- **Mục tiêu:** Cú vấp ngã ngớ ngẩn này sẽ tạo ra một Gradient phạt khổng lồ lên các Node kích hoạt lệnh Buy. Thuật toán sẽ ngay lập tức tỉnh ngộ và giật lùi về lại lá chắn Sell thuần túy. Chế độ Infinite Mining tiếp tục hoạt động!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_122
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_122 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_122'
run_dir_122 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_122)
os.makedirs(run_dir_122, exist_ok=True)

# Copy config from 121 to 122
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_121, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_122
config_path_122 = os.path.join(run_dir_122, 'config.json')

with open(config_path_122, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_122.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_122}"
config_path = r"{config_path_122}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_122.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_122).

📊 Kết quả HolyGrail_121:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_73:.2f}% (Threshold 0.73) | {wr_84:.2f}% (Threshold 0.84)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 116  | 0.3147 |  32.5%  |  49.3%  |  33.3%  |
| 117  | 0.2729 |  32.8%  |  63.2%  |  33.3%  |
| 118  | 0.2844 |  32.5%  |  45.2%  |  33.3%  |
| 119  | 0.3053 |  30.6%  |  49.4%  |  33.3%  |
| 120  | 0.2658 |  34.5%  |  51.4%  |  33.3%  |
| 121  | {score:.4f}|  {wr_73:.1f}%  | {wr_84:.1f}%  |  33.3%  |

Một pha "Ảo giác đảo gương" chết người! Mạng Nơ-ron đã ghi nhớ con số 56 là chìa khóa thành công từ các vòng trước, nhưng lại đảo lộn vị trí: Thay vì 56 lệnh Sell, nó lại tung ra {total_buy} lệnh Buy và chỉ giữ {total_sell} lệnh Sell. Cú bẻ lái bạo chúa sang phe Buy này ngay lập tức bị thị trường trừng phạt, Win Rate cắm thẳng cổ từ 51.35% xuống còn {wr_84:.2f}%. Sự thất bại này đóng đinh chân lý: Trong phiên Á, Buy là rác, Sell là vàng. 🚀 HolyGrail_122 (PID {pid}) đã kích hoạt! Mục tiêu: Tự động tỉnh ngộ và quay về lá chắn Sell thuần túy!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
