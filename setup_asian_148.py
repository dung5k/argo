# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_147
run_id_147 = "run_20260515_010727_v6_ASIAN_15m_TP5_SL25_BigBrain_147"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_147, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 147 (BigBrain_147):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_86:.2f}%** (Threshold 0.86).
- **Phân tích Sâu:** TỌA ĐỘ PHẢN-KIM-CƯƠNG (ANTI-DIAMOND COORDINATE)! Một hiện tượng chấn động vừa xảy ra! Đòn đánh tầm trung (LR 1.5e-4) đã đánh bật mạng lưới khỏi cái hố 39%. Tuy nhiên, lực văng đã ném nó cắm phập sang thái cực hoàn toàn đối lập. Thay vì tạo ra "0 Buy", nó đã tạo ra **{total_buy} lệnh Buy** và xóa sổ hoàn toàn phe Sell (**{total_sell} lệnh Sell**). Đây là sự kiện Đảo Cực Tuyệt Đối (100% Buy)! Đáng kinh ngạc là ở cái rốn của sườn dốc Buy này, Win Rate vẫn đạt **{wr_86:.2f}%**, chứng tỏ có một túi thanh khoản Buy rất mạnh ở đây. Dù vậy, đối với phiên Á, nghiêng 100% về Buy là một cấu trúc rủi ro cực cao khi thị trường xả hàng.

### Ý tưởng tiếp theo (Vòng 148 - BigBrain_148):
- **Hành động:** Chạy tiếp Vòng 148. Tung Đòn Đánh Tinh Khắc (Precision Strike): Điều chỉnh Learning Rate về `8.0e-5` và siết Dropout ở `0.20`.
- **Mục tiêu:** Chúng ta đang nảy qua nảy lại giữa hai sườn dốc: 1.5e-4 ném thẳng sang dốc 100% Buy, còn 1.0e-4 (ở V144) ném về dốc 7 Buy / 38 Sell. Để rơi trúng điểm chính giữa (0 Buy / 65 Sell), chúng ta cần một lực lượng giác tinh vi hơn. Cú đánh `LR=8.0e-5` được tính toán để gõ nhẹ mạng lưới văng khỏi hố Phản-Kim-Cương này, trượt nhẹ qua đỉnh đồi và hạ cánh chính xác vào vùng phòng thủ Sell tuyệt đối!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_148
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_148 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_148'
run_dir_148 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_148)
os.makedirs(run_dir_148, exist_ok=True)

# Copy config from 147 to 148 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_147, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY PRECISION STRIKE THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 8.0e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_148
config_path_148 = os.path.join(run_dir_148, 'config.json')

with open(config_path_148, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_148.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_148}"
config_path = r"{config_path_148}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_148.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_148).

📊 Kết quả HolyGrail_147:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_86:.2f}% (Threshold 0.86)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 142  | 0.2881 |  33.1%  |  37.3%  |  33.3%  |
| 143  | 0.3277 |  37.6%  |  43.8%  |  33.3%  |
| 144  | 0.3015 |  38.3%  |  51.1%  |  33.3%  |
| 145  | 0.2782 |  33.1%  |  48.0%  |  33.3%  |
| 146  | 0.2898 |  34.0%  |  39.1%  |  33.3%  |
| 147  | {score:.4f}|  {wr_75:.1f}%  | {wr_86:.1f}%  |  33.3%  |

TỌA ĐỘ PHẢN-KIM-CƯƠNG (ANTI-DIAMOND)! Một sự kiện kinh thiên động địa vừa xảy ra! Đòn đánh 1.5e-4 đã xóa sổ hoàn toàn phe Sell ({total_sell} lệnh) và bùng nổ phe Buy lên {total_buy} lệnh! Nó tạo ra một Tọa độ Phản-Kim-Cương ngược đời: Nghiêng 100% về lệnh Buy. Dù vậy, mạng lưới vẫn tìm thấy một vũng thanh khoản ẩn giúp Win Rate đạt {wr_86:.2f}%. Tuy nhiên, đây là cấu hình cực kỳ rủi ro cho phiên Á Ranging. 🚀 HolyGrail_148 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Đòn Đánh Tinh Khắc (Precision Strike) với LR 8.0e-5 và Dropout 0.20. Cú gõ nhẹ này được tính toán kỹ lưỡng để hất văng mạng lưới khỏi hố Buy 100%, trượt qua đỉnh đồi và hạ cánh chính xác vào vùng phòng thủ Sell tuyệt đối!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
