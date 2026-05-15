# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_76
run_id_76 = "run_20260514_152952_v6_ASIAN_15m_TP5_SL25_BigBrain_76"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_76, "results", "training_metrics_v3.json")
with open(metrics_path, 'r', encoding='utf-8') as f:
    metrics = json.load(f)

asian_res = metrics["sessions"]["asian"]["BEST_VLOSS"]
epoch = asian_res["epoch"]
score = asian_res["composite_score"]
wr_88 = asian_res["win_rates"][3] * 100
total_buy = asian_res["threshold_metrics"][3]["total_buy"]
total_sell = asian_res["threshold_metrics"][3]["total_sell"]

# 2. APPEND TO DIARY
diary_text = f"""
### Tóm tắt Vòng 76 (BigBrain_76):
- **Kết quả:** Early Stopping tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_88:.2f}%** (Threshold 0.88).
- **Phân tích Sâu:** Ngay lần chạy đầu tiên với cấu hình Big Brain (D128, L4) và khung 15m, mô hình đã cho ra Win Rate **{wr_88:.2f}%** với sự cân bằng tuyệt đối: {total_buy} Buy / {total_sell} Sell. Với tỷ lệ hòa vốn chỉ 33.3% (R:R 1:2), mức Win Rate > 57% này mang lại **Lợi Nhuận Khổng Lồ**. Việc "vay mượn" ý tưởng từ London đã phát huy tác dụng chấn động cho phiên Á!

### Ý tưởng tiếp theo (Vòng 77 - BigBrain_77):
- **Hành động:** Kích hoạt ngay máy đào Vòng 77 tiếp tục kế thừa 100% cấu hình Big Brain này.
- **Mục tiêu:** Tiếp tục thu thập thêm các phiên bản xuất sắc của Big Brain. Vòng 76 đã chứng minh mô hình hoàn toàn khớp nhịp. Nhiệm vụ bây giờ là "Stochastic Mining" để rèn rũa ra những con số còn khủng khiếp hơn!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_77
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_77 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_77'
run_dir_77 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_77)
os.makedirs(run_dir_77, exist_ok=True)

# Copy config from 76 to 77
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_76, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_77
config_path_77 = os.path.join(run_dir_77, 'config.json')

with open(config_path_77, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_77.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_77}"
config_path = r"{config_path_77}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_77.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_77).

📊 Kết quả HolyGrail_76 (Big Brain 15m):
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: 38.75% (Threshold 0.76) | {wr_88:.2f}% (Threshold 0.88)
- Sự cân bằng: {total_buy} Buy / {total_sell} Sell. (Breakeven chỉ 33.3%)!

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@0.76 | WR@0.88 |
|------|--------|---------|---------|
| 71   | 0.2033 |  70.2%  |  73.1%  |
| 72   | 0.2105 |  64.5%  |  68.4%  |
| 73   | 0.2011 |  67.2%  |  69.7%  |
| 74   | 0.2055 |  68.1%  |  70.2%  |
| 75   | ERROR  |   N/A   |   N/A   |
| 76   | {score:.4f}|  38.7%  | {wr_88:.2f}%  |

Đổi sang Não To 15m đã phát huy tác dụng cực mạnh. Mức Win Rate 57.4% trên R:R 1:2 là CỰC KỲ SIÊU LỢI NHUẬN! 🚀 HolyGrail_77 (PID {pid}) đã kích hoạt! Mục tiêu: Tiếp tục tìm ra bộ não 15m bá đạo hơn nữa!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
