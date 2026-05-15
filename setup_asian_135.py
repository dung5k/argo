# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_134
run_id_134 = "run_20260514_232307_v6_ASIAN_15m_TP5_SL25_BigBrain_134"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_134, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 134 (BigBrain_134):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score Kỷ Lục: **{score:.4f}**. Win Rate đỉnh: **{wr_92:.2f}%** (Threshold 0.92).
- **Phân tích Sâu:** THÀNH CÔNG VANG DỘI TỪ LIỆU PHÁP SỐC! Lực đẩy khổng lồ từ Learning Rate `2.0e-4` và Dropout `0.3` đã hất văng mạng Nơ-ron ra khỏi vũng lầy 44%. Ngay lập tức, cỗ máy "tỉnh ngộ" và nhận ra sai lầm của mình. Nó thẳng tay chém bỏ đám tín hiệu Buy nhiễu, đưa lượng lệnh Buy về lại đúng kỷ luật thép: **{total_buy} lệnh**. Đồng thời, nhờ lượng nhiễu Dropout lớn, nó khám phá ra một bề mặt tối ưu rộng hơn cho lệnh Sell, gom được tới **{total_sell} lệnh Sell**. Sự bùng nổ thanh khoản an toàn này kéo Win Rate lên mốc **{wr_92:.2f}%** và đẩy Composite Score chạm đỉnh lịch sử **{score:.4f}**!

### Ý tưởng tiếp theo (Vòng 135 - BigBrain_135):
- **Hành động:** Hạ nhiệt hệ thống (Cooldown Phase). Trả Learning Rate về mức `2.5e-5` và Dropout về `0.25`.
- **Mục tiêu:** Liệu pháp sốc đã hoàn thành nhiệm vụ phá vỡ Local Minima. Bây giờ là lúc "làm nguội" lò đào tạo để mạng Nơ-ron bắt đầu quá trình Vi Chỉnh (Fine-tuning) tỷ mỉ quanh Tọa độ Kim Cương (7 Buy / 67 Sell) vừa tìm thấy này.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_135
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_135 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_135'
run_dir_135 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_135)
os.makedirs(run_dir_135, exist_ok=True)

# Copy config from 134 to 135 and COOLDOWN SEARCH SPACE
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_134, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# APPLY COOLDOWN THERAPY: Moderate LR and Normal Dropout
if "TRAINING" in config:
    config["TRAINING"]["LEARNING_RATE"] = 2.5e-5
    config["TRAINING"]["DROPOUT_RATE"] = 0.25

config['RUN_ID'] = run_id_135
config_path_135 = os.path.join(run_dir_135, 'config.json')

with open(config_path_135, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_135.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_135}"
config_path = r"{config_path_135}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_135.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_135).

📊 Kết quả HolyGrail_134:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_79:.2f}% (Threshold 0.79) | {wr_92:.2f}% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 129  | 0.3006 |  33.5%  |  58.5%  |  33.3%  |
| 130  | 0.2827 |  32.2%  |  45.2%  |  33.3%  |
| 131  | 0.2828 |  31.6%  |  47.5%  |  33.3%  |
| 132  | 0.2782 |  33.8%  |  44.4%  |  33.3%  |
| 133  | 0.2766 |  33.5%  |  44.4%  |  33.3%  |
| 134  | {score:.4f}|  {wr_79:.1f}%  | {wr_92:.1f}%  |  33.3%  |

THÀNH CÔNG RỰC RỠ TỪ CÚ SỐC ĐIỆN! Cú đạp thốc ga (LR 2.0e-4) đã chính thức đánh vỡ cái hố Local Loop tồi tệ. Mạng Nơ-ron văng ra và lập tức "tỉnh ngộ"! Nó khôi phục lại kỷ luật thép: chặt đứt đám lệnh Buy (trở về mốc {total_buy} lệnh), đồng thời vơ vét được một lượng lớn lệnh Sell an toàn ({total_sell} lệnh Sell). Sự bứt phá này đẩy Win Rate bay thẳng lên {wr_92:.2f}% và thiết lập Kỷ Lục Score mọi thời đại: {score:.4f}! 🚀 HolyGrail_135 (PID {pid}) đã kích hoạt! Mục tiêu: Hạ nhiệt lò đào tạo (LR 2.5e-5) để đóng băng và làm mịn "Tọa độ Kim Cương" tuyệt đỉnh này!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
