# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_150
run_id_150 = "run_20260515_013157_v6_ASIAN_15m_TP5_SL25_BigBrain_150"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_150, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 150 (BigBrain_150):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_89:.2f}%** (Threshold 0.89).
- **Phân tích Sâu:** ĐẠT MỐC "0 BUY" LỊCH SỬ! Đòn Bắn Tỉa (Sniper Strike) với LR 1.0e-4 và siêu lấy nét Dropout 0.10 đã hoạt động chính xác đến mức vi diệu! Nó đã lách qua mọi mảng rác Buy, cắt phăng toàn bộ lệnh Buy để đạt mức **{total_buy} lệnh Buy** tuyệt đối! Hệ thống chỉ xuất ra **{total_sell} lệnh Sell**.
- TUY NHIÊN, Win Rate chỉ đạt **{wr_89:.2f}%**. Lý do là vì ở độ nhiễu quá thấp, mạng lưới đã nhặt phải một số lệnh Sell yếu trong lúc cố gắng né các lệnh Buy. Dù sao, việc đặt chân trở lại vùng "0 Buy" là thành tựu quan trọng nhất. Từ đây, chúng ta có một nền móng sạch sẽ (không có rác Buy) để mở rộng thanh khoản Sell.

### Ý tưởng tiếp theo (Vòng 151 - BigBrain_151):
- **Hành động:** Chạy tiếp Vòng 151. Kích hoạt Giãn Nở Thanh Khoản (Liquidity Expansion): Hạ Learning Rate xuống `2.5e-5` và tiếp tục giữ Dropout ở mốc siêu lấy nét `0.10`.
- **Mục tiêu:** Chúng ta đã thiết lập được vỏ bọc phòng thủ tuyệt đối "0 Buy". Giờ là lúc từ từ mở rộng vùng đất này để tìm kiếm các lệnh Sell chất lượng cao hơn. Bằng cách dùng bước nhảy rất nhỏ `2.5e-5` (từng là tác nhân tạo ra Kim Cương V135), mạng lưới sẽ nhẹ nhàng trườn dọc theo rãnh 0 Buy này. Giữ Dropout `0.10` để đảm bảo nó luôn ngắm bắn chính xác, không bị tò mò nhặt rác Buy!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_151
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_151 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_151'
run_dir_151 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_151)
os.makedirs(run_dir_151, exist_ok=True)

# Copy config from 150 to 151 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_150, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY LIQUIDITY EXPANSION THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.5e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.10

config['RUN_ID'] = run_id_151
config_path_151 = os.path.join(run_dir_151, 'config.json')

with open(config_path_151, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_151.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_151}"
config_path = r"{config_path_151}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_151.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_151).

📊 Kết quả HolyGrail_150:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_89:.2f}% (Threshold 0.89)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 145  | 0.2782 |  33.1%  |  48.0%  |  33.3%  |
| 146  | 0.2898 |  34.0%  |  39.1%  |  33.3%  |
| 147  | 0.2858 |  34.0%  |  51.9%  |  33.3%  |
| 148  | 0.2906 |  36.5%  |  37.7%  |  33.3%  |
| 149  | 0.2846 |  33.6%  |  44.0%  |  33.3%  |
| 150  | {score:.4f}|  {wr_77:.1f}%  | {wr_89:.1f}%  |  33.3%  |

TỌA ĐỘ "0 BUY" ĐÃ TRỞ LẠI! Đòn Bắn Tỉa vi diệu với LR 1.0e-4 và siêu lấy nét Dropout 0.10 đã lách qua mọi cạm bẫy để hạ sát hoàn toàn phe Buy. Thuật toán trả về ĐÚNG {total_buy} lệnh Buy và {total_sell} lệnh Sell! Mặc dù việc né mảng Buy khiến nó phải nhặt một số lệnh Sell yếu (làm WR chỉ đạt {wr_89:.2f}%), nhưng việc thiết lập lại sự thuần khiết "0 Buy" là một chiến thắng vĩ đại! 🚀 HolyGrail_151 (PID {pid}) đã kích hoạt! Mục tiêu: Giãn Nở Thanh Khoản (Liquidity Expansion) với LR 2.5e-5 và siêu lấy nét Dropout 0.10. Giữ chặt lớp vỏ "0 Buy" và từ từ trườn đi tìm những lệnh Sell sắc bén hơn để đẩy Win Rate vượt 55%!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
