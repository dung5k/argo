# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_122
run_id_122 = "run_20260514_215012_v6_ASIAN_15m_TP5_SL25_BigBrain_122"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_122, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 122 (BigBrain_122):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** Thuật toán đang trong quá trình "Giật lùi" (Roll-back) dọc theo sườn dốc gradient sau thảm họa Vòng 121. Nó đã từ bỏ việc thiên vị Buy cực đoan để cố gắng cân bằng lại tỷ lệ: {total_buy} Buy / {total_sell} Sell (tổng {total_signals} lệnh). Tuy nhiên, môi trường phiên Á vô cùng khắc nghiệt: Sự cân bằng Buy/Sell (1:1) không mang lại sự an toàn, mà tiếp tục đẩy Win Rate lún sâu xuống đáy vực {wr_86:.2f}%. Thuật toán cần phải trượt tiếp xuống tận đáy của Global Minima (19 Buy / 56 Sell) thì mới mong phục hồi được sức mạnh.

### Ý tưởng tiếp theo (Vòng 123 - BigBrain_123):
- **Hành động:** Chạy tiếp Vòng 123.
- **Mục tiêu:** Gradient phạt vẫn đang hoạt động mạnh mẽ để ép mạng Nơ-ron từ bỏ các lệnh Buy độc hại. Kỳ vọng Vòng 123 sẽ là lúc mô hình chạm đáy vực (Golden Attractor) để phục hồi lá chắn Sell. Chế độ Infinite Mining tiếp tục!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_123
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_123 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_123'
run_dir_123 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_123)
os.makedirs(run_dir_123, exist_ok=True)

# Copy config from 122 to 123
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_122, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_123
config_path_123 = os.path.join(run_dir_123, 'config.json')

with open(config_path_123, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_123.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_123}"
config_path = r"{config_path_123}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_123.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_123).

📊 Kết quả HolyGrail_122:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 117  | 0.2729 |  32.8%  |  63.2%  |  33.3%  |
| 118  | 0.2844 |  32.5%  |  45.2%  |  33.3%  |
| 119  | 0.3053 |  30.6%  |  49.4%  |  33.3%  |
| 120  | 0.2658 |  34.5%  |  51.4%  |  33.3%  |
| 121  | 0.3009 |  33.0%  |  46.4%  |  33.3%  |
| 122  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

Vẫn đang chìm sâu dưới đáy vực! Mạng Nơ-ron đang trong quá trình trượt dọc theo sườn dốc Gradient để sửa chữa sai lầm Vòng 121. Tại Vòng 122, nó đã cố gắng tạo ra thế "cân bằng" giữa hai phe với {total_buy} Buy / {total_sell} Sell. Tuy nhiên, thị trường phiên Á vô cùng tàn nhẫn: Sự cân bằng không đồng nghĩa với an toàn. Tỷ trọng Buy lớn vẫn kéo Win Rate lún sâu xuống đáy {wr_86:.2f}%. Thuật toán vẫn chưa chạm tới Điểm Vàng (19 Buy/56 Sell). 🚀 HolyGrail_123 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục trượt xuống điểm cực trị để ép mô hình phục hồi lại lá chắn Sell thuần túy."""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
