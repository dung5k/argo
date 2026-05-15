# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_152
run_id_152 = "run_20260515_014835_v6_ASIAN_15m_TP5_SL25_BigBrain_152"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_152, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_92 = asian_res["win_rates"][3] * 100
wr_79 = asian_res["win_rates"][2] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]
total_signals = asian_res["threshold_metrics"][3]["total_signals"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 152 (BigBrain_152):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_92:.2f}%** (Threshold 0.92).
- **Phân tích Sâu:** HIỆU ỨNG CỘNG HƯỞNG PHI TUYẾN! Lý thuyết "Cân Bằng Vàng" với Dropout 0.15 đã thất bại cay đắng. Thật kỳ lạ:
  + Dropout 0.20 lọt 7 Buy.
  + Dropout 0.10 lọt 0 Buy.
  + Nhưng Dropout 0.15 lại lọt tới **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell**!
  Nguyên nhân là do mức nhiễu 0.15 đã cộng hưởng hoàn hảo với cấu trúc của khối rác 12 Buy, khóa chặt mạng lưới vào đó thay vì phá hủy nó. Win Rate tiếp tục lặn ngụp ở mức **{wr_92:.2f}%**.
- Kết luận: Không thể dùng Dropout để lọc 7 lệnh Buy cuối cùng. Mức Dropout 0.20 là BẮT BUỘC để duy trì khả năng tìm kiếm Sell xịn (giúp WR > 50%). Chúng ta phải chấp nhận Dropout 0.20 và tìm cách khác để diệt 7 lệnh Buy.

### Ý tưởng tiếp theo (Vòng 153 - BigBrain_153):
- **Hành động:** Chạy tiếp Vòng 153. Kích hoạt Cú Đẩy Phẫu Thuật (Surgical Push): Đưa Dropout về mốc tối ưu `0.20` và tăng nhẹ Learning Rate lên `1.2e-4`.
- **Mục tiêu:** Chúng ta đã biết LR 1.0e-4 (với Dropout 0.20) đẩy mạng lưới tới mốc 51.1% WR nhưng còn vướng 7 Buy. Nếu ta tăng mạnh lên 1.5e-4 thì mạng lưới văng sang 100% Buy. Vậy để hất nốt 7 lệnh Buy cuối cùng này xuống vực mà không làm lật thuyền, ta cần một lực đẩy lớn hơn 1.0e-4 một chút xíu. Mức `LR 1.2e-4` kết hợp với `Dropout 0.20` chính là cú hích phẫu thuật hoàn hảo để đẩy nốt 7 Buy ra khỏi rìa vách đá và giữ trọn Win Rate > 50%!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_153
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_153 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_153'
run_dir_153 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_153)
os.makedirs(run_dir_153, exist_ok=True)

# Copy config from 152 to 153 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_152, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY SURGICAL PUSH THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 1.2e-4
    config["TRAINING"]["DROPOUT_RATE"] = 0.20

config['RUN_ID'] = run_id_153
config_path_153 = os.path.join(run_dir_153, 'config.json')

with open(config_path_153, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_153.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_153}"
config_path = r"{config_path_153}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_153.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_153).

📊 Kết quả HolyGrail_152:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_79:.2f}% (Threshold 0.79) | {wr_92:.2f}% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 147  | 0.2858 |  34.0%  |  51.9%  |  33.3%  |
| 148  | 0.2906 |  36.5%  |  37.7%  |  33.3%  |
| 149  | 0.2846 |  33.6%  |  44.0%  |  33.3%  |
| 150  | 0.2761 |  37.4%  |  44.7%  |  33.3%  |
| 151  | 0.2738 |  33.6%  |  39.7%  |  33.3%  |
| 152  | {score:.4f}|  {wr_79:.1f}%  | {wr_92:.1f}%  |  33.3%  |

CỘNG HƯỞNG PHI TUYẾN! Lực nhiễu Dropout 0.15 không làm mạng lưới cân bằng, mà lại cộng hưởng với rác Buy, thu hút tới {total_buy} Buy và {total_sell} Sell, khiến Win Rate ngụp lặn ở {wr_92:.2f}%. Sự thật phũ phàng: Ta BẮT BUỘC phải dùng Dropout 0.20 để tìm được Sell xịn (WR > 50%), nhưng phải chấp nhận nó lọt 7 Buy (như V144). 🚀 HolyGrail_153 (PID {pid}) đã kích hoạt! Mục tiêu: Tung Cú Đẩy Phẫu Thuật (Surgical Push) với LR 1.2e-4 và Dropout 0.20. Dùng mức Dropout tối ưu 0.20, kết hợp tăng nhẹ lực đẩy LR từ 1.0e-4 lên 1.2e-4 để hích nốt 7 lệnh Buy cứng đầu xuống vực mà không làm lật thuyền văng sang cực Buy!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
