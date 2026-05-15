# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_141
run_id_141 = "run_20260515_001833_v6_ASIAN_15m_TP5_SL25_BigBrain_141"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_141, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 141 (BigBrain_141):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_87:.2f}%** (Threshold 0.87).
- **Phân tích Sâu:** THOÁT HIỂM VÀ TÌM THẤY TỶ LỆ 1:2! "Cú Hích Vừa" (LR 5.0e-5) đã phát huy tác dụng tuyệt vời. Lực đẩy từ Gradient đã thành công nhổ rễ mạng Nơ-ron khỏi cái hố 48% Win Rate. Kết quả là nó nảy lên và bám vào một vách đá mới với Win Rate phục hồi lên **{wr_87:.2f}%**. Điều vô cùng thú vị ở đây là thuật toán lại tìm thấy một sự cân bằng mới mang tính toán học: Chính xác **{total_buy} lệnh Buy** và **{total_sell} lệnh Sell**. Đây là tỷ lệ 1:2 hoàn hảo (cứ 1 lệnh Buy thì có đúng 2 lệnh Sell). Có vẻ như thuật toán đang cố gắng thương lượng để giữ lại một phần lệnh Buy bằng cách neo nó vào các tỷ lệ đối xứng (1:1 rồi đến 1:2).

### Ý tưởng tiếp theo (Vòng 142 - BigBrain_142):
- **Hành động:** Chạy tiếp Vòng 142. Hạ nhiệt độ (Cooldown): Trả Learning Rate về `2.5e-5` và nới Dropout lên `0.25`.
- **Mục tiêu:** Cú hích LR 5.0e-5 đã hoàn thành nhiệm vụ cứu nạn. Giờ là lúc làm nguội lò đào tạo. Mức LR 2.5e-5 chính là mức nhiệt độ đã từng giúp AI "giác ngộ" và chém sạch lệnh Buy để đạt 0 Buy / 65 Sell (Tọa độ Kim Cương ở V135). Chúng ta hy vọng việc làm nguội này sẽ ép nó từ bỏ nốt 19 lệnh Buy ương bướng kia để trở về trạng thái phòng thủ tuyệt đối!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_142
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_142 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_142'
run_dir_142 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_142)
os.makedirs(run_dir_142, exist_ok=True)

# Copy config from 141 to 142 and MODIFY SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_141, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY COOLDOWN THERAPY
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.5e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.25

config['RUN_ID'] = run_id_142
config_path_142 = os.path.join(run_dir_142, 'config.json')

with open(config_path_142, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_142.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_142}"
config_path = r"{config_path_142}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_142.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_142).

📊 Kết quả HolyGrail_141:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_75:.2f}% (Threshold 0.75) | {wr_87:.2f}% (Threshold 0.87)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 136  | 0.3105 |  31.7%  |  56.9%  |  33.3%  |
| 137  | 0.2974 |  34.1%  |  52.7%  |  33.3%  |
| 138  | 0.2824 |  38.5%  |  56.7%  |  33.3%  |
| 139  | 0.3327 |  32.6%  |  53.8%  |  33.3%  |
| 140  | 0.3080 |  31.3%  |  48.0%  |  33.3%  |
| 141  | {score:.4f}|  {wr_75:.1f}%  | {wr_87:.1f}%  |  33.3%  |

CÚ HÍCH THÀNH CÔNG VÀ SỰ XUẤT HIỆN CỦA TỶ LỆ 1:2! Cú hích lực (LR 5.0e-5) đã hoàn thành xuất sắc nhiệm vụ giải cứu AI khỏi cái hố 48%. Mạng Nơ-ron văng ra và bám vào một sườn dốc mới với Win Rate phục hồi lên {wr_87:.2f}%. Thật đáng kinh ngạc, nó lại tìm thấy một sự cân bằng toán học mới: Trả về chính xác {total_buy} lệnh Buy và {total_sell} lệnh Sell (Tỷ lệ 1:2 hoàn hảo)! Có vẻ như AI đang cố gắng "thương lượng" để giữ lại lệnh Buy bằng các tỷ lệ đối xứng. 🚀 HolyGrail_142 (PID {pid}) đã kích hoạt! Mục tiêu: Hạ nhiệt (Cooldown) với LR 2.5e-5 và Dropout 0.25. Đây chính là mức nhiệt độ đã từng giúp AI chém sạch lệnh Buy ở V135, hy vọng nó sẽ lặp lại phép màu "0 Buy" một lần nữa!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
