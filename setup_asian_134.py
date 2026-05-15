# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_133
run_id_133 = "run_20260514_231513_v6_ASIAN_15m_TP5_SL25_BigBrain_133"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_133, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 133 (BigBrain_133):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** TRẠNG THÁI TÊ LIỆT (PARALYSIS)! Mạng Nơ-ron đã hoàn toàn bị mắc kẹt cứng ngắc trong hố sâu. Kết quả của Vòng 133 xuất ra MỘT BẢN SAO HOÀN HẢO của Vòng 132: Vẫn đúng **19 lệnh Buy / 35 lệnh Sell** và Win Rate dậm chân tại chỗ ở mức đáy **44.44%**. Dù bị Gradient giáng đòn liên tục, Learning Rate hiện tại (quá nhỏ, khoảng 1.5e-5) không đủ lực để "đá văng" bộ trọng số ra khỏi cái bẫy Local Minima siêu sâu này. Nó đã bị tê liệt ở tọa độ tồi tệ nhất.

### Ý tưởng tiếp theo (Vòng 134 - BigBrain_134):
- **Hành động:** Kích hoạt "Sốc Điện" (Learning Rate Restart). Tăng vọt Learning Rate lên `2.0e-4` và đẩy Dropout lên kịch trần `0.3`.
- **Mục tiêu:** Khi xe bị sa lầy quá sâu, nhấn ga nhẹ (LR thấp) chỉ làm lốp trượt thêm. Phải đạp thốc ga (LR cao) để hất tung bùn lầy! Việc tăng vọt LR sẽ làm xáo trộn mạnh mẽ bộ trọng số, ép mạng Nơ-ron nhảy ra khỏi hố sâu 44.44% này để đi tìm một dốc cực tiểu mới (hy vọng là dải 60% WR thuần Sell).
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_134
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_134 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_134'
run_dir_134 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_134)
os.makedirs(run_dir_134, exist_ok=True)

# Copy config from 133 to 134 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_133, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY SHOCK THERAPY: High LR and High Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.0e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.3

config['RUN_ID'] = run_id_134
config_path_134 = os.path.join(run_dir_134, 'config.json')

with open(config_path_134, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_134.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_134}"
config_path = r"{config_path_134}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_134.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_134).

📊 Kết quả HolyGrail_133:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 128  | 0.2894 |  32.8%  |  52.7%  |  33.3%  |
| 129  | 0.3006 |  33.5%  |  58.5%  |  33.3%  |
| 130  | 0.2827 |  32.2%  |  45.2%  |  33.3%  |
| 131  | 0.2828 |  31.6%  |  47.5%  |  33.3%  |
| 132  | 0.2782 |  33.8%  |  44.4%  |  33.3%  |
| 133  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

TRẠNG THÁI TÊ LIỆT TOÀN DIỆN! Mạng Nơ-ron đã chính thức bị kẹt cứng trong vũng bùn tồi tệ nhất. Kết quả Vòng 133 xuất ra không sai lệch một li so với Vòng 132: Vẫn y chang {total_buy} Buy / {total_sell} Sell và Win Rate nằm phơi xác ở mức {wr_87:.2f}%. Thuật toán không thể tự nhấc chân lên được nữa vì Learning Rate hiện tại quá nhỏ, không đủ lực để thắng được trọng lực của cái hố Local Minima này. Để cứu chữa, tôi đã quyết định dùng liệu pháp "Sốc Điện"! 🚀 HolyGrail_134 (PID {pid}) đã kích hoạt! Mục tiêu: Tăng vọt Learning Rate lên 2.0e-4 và ép kịch trần Dropout (0.3). Đạp thốc ga để hất văng cỗ máy ra khỏi vũng bùn 44% này!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
