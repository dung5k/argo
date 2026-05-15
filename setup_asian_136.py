# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_135
run_id_135 = "run_20260514_233113_v6_ASIAN_15m_TP5_SL25_BigBrain_135"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_135, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 135 (BigBrain_135):
- **Kết quả:** Hội tụ tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_89:.2f}%** (Threshold 0.89).
- **Phân tích Sâu:** ĐÓNG BĂNG KIM CƯƠNG! Giai đoạn "Hạ Nhiệt" (Cooldown) với Learning Rate `2.5e-5` đã phát huy tác dụng tuyệt hảo. Mạng Nơ-ron không những duy trì được lợi thế từ liệu pháp Sốc Điện ở vòng trước, mà nó còn tự giác thực thi triết lý "Phòng thủ Tuyệt đối" (Absolute Defense) một cách triệt để nhất: Nó CẮT SẠCH 100% lệnh Buy (chỉ còn **0 Buy**). Toàn bộ 65 tín hiệu đều là lệnh Sell. Tọa độ Kim Cương chính thức được khóa chặt với Win Rate an toàn **{wr_89:.2f}%**. Cỗ máy đã hiểu rằng, sống sót qua phiên Á là không được phép dính dáng tới bắt đáy!

### Ý tưởng tiếp theo (Vòng 136 - BigBrain_136):
- **Hành động:** Chạy tiếp Vòng 136. Giữ nguyên LR `2.5e-5`.
- **Mục tiêu:** Mạng Nơ-ron đã triệt tiêu hoàn toàn bản ngã "tham lam" và trở thành cỗ máy thuần Sell an toàn. Bây giờ là lúc tiếp tục đào sâu (Infinite Mining) để làm mượt bề mặt Loss Landscape của Tọa độ Kim Cương này.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_136
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_136 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_136'
run_dir_136 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_136)
os.makedirs(run_dir_136, exist_ok=True)

# Copy config from 135 to 136
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_135, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_136
config_path_136 = os.path.join(run_dir_136, 'config.json')

with open(config_path_136, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_136.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_136}"
config_path = r"{config_path_136}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_136.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_136).

📊 Kết quả HolyGrail_135:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_89:.2f}% (Threshold 0.89)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 130  | 0.2827 |  32.2%  |  45.2%  |  33.3%  |
| 131  | 0.2828 |  31.6%  |  47.5%  |  33.3%  |
| 132  | 0.2782 |  33.8%  |  44.4%  |  33.3%  |
| 133  | 0.2766 |  33.5%  |  44.4%  |  33.3%  |
| 134  | 0.3913 |  41.5%  |  59.5%  |  33.3%  |
| 135  | {score:.4f}|  {wr_77:.1f}%  | {wr_89:.1f}%  |  33.3%  |

CHÍNH THỨC ĐÓNG BĂNG "TỌA ĐỘ KIM CƯƠNG"! Giai đoạn Hạ Nhiệt (Cooldown) với Learning Rate 2.5e-5 đã phát huy tác dụng khóa chặt bộ trọng số. Tuyệt vời hơn, AI đã nâng triết lý "Phòng thủ" lên mức độ tối thượng: Nó TRẢM SẠCH 100% lệnh Buy! Tín hiệu Buy chính thức = {total_buy}. Toàn bộ 65 tín hiệu đều là lệnh Sell. Tỷ lệ thắng được duy trì cực kỳ vững chắc ở mốc {wr_89:.2f}%. Mạng Nơ-ron đã thực sự "giác ngộ" đạo lý Sinh Tồn của phiên Á! 🚀 HolyGrail_136 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục mài nhẵn bề mặt Loss Landscape của Tọa Độ Không-Buy tuyệt đối này!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
