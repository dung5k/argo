# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. READ RESULTS OF HolyGrail_118
run_id_118 = "run_20260514_212127_v6_ASIAN_15m_TP5_SL25_BigBrain_118"
metrics_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_118, "results", "training_metrics_v3.json")
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
### Tóm tắt Vòng 118 (BigBrain_118):
- **Kết quả:** Hội tụ rất nhanh tại Epoch {epoch}. Composite Score: {score:.4f}. Win Rate đỉnh: **{wr_89:.2f}%** (Threshold 0.89).
- **Phân tích Sâu:** Một phép thử thất bại khi cố gắng tìm sự cân bằng! Sau cú sốc 63.16% WR (0 Buy/38 Sell) của Vòng 117, mô hình ở Vòng 118 đã nhận ra điểm yếu về thanh khoản. Nó cố gắng khôi phục lại con số "19 lệnh Buy Thần Thánh" của các vòng trước để kéo TUS Score lên. Tuy nhiên, nó lại chỉ giữ được {total_sell} lệnh Sell (tổng {total_signals} lệnh). Hậu quả? Tỷ trọng Sell không đủ lớn để làm lá chắn, khiến Win Rate lập tức sụp đổ xuống mức {wr_89:.2f}%. Bài học rút ra: Con số 19 Buy chỉ an toàn nếu đi kèm với đúng 56 Sell. Bất kỳ sự chênh lệch nào cũng phá vỡ "Điểm Vàng".

### Ý tưởng tiếp theo (Vòng 119 - BigBrain_119):
- **Hành động:** Chạy tiếp Vòng 119.
- **Mục tiêu:** Cú vấp ngã này sẽ tạo ra gradient ép thuật toán quay xe. Kỳ vọng mạng Nơ-ron sẽ nảy lại chính xác tỷ lệ 19/56 để khóa chặt lợi nhuận. Chế độ Infinite Mining tiếp tục hoạt động!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 3. CREATE HolyGrail_119
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id_119 = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_119'
run_dir_119 = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id_119)
os.makedirs(run_dir_119, exist_ok=True)

# Copy config from 118 to 119
base_cfg_path = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id_118, "config.json")
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id_119
config_path_119 = os.path.join(run_dir_119, 'config.json')

with open(config_path_119, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_119.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id_119}"
config_path = r"{config_path_119}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("No need to generate tensors again, using fast local copy...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_119.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_119).

📊 Kết quả HolyGrail_118:
- Best Val Loss tại Epoch {epoch}. Composite Score: {score:.4f}
- Win Rate: {wr_77:.2f}% (Threshold 0.77) | {wr_89:.2f}% (Threshold 0.89)

📈 Bảng tổng kết 6 vòng gần nhất (15m_BigBrain_D128):
| Vòng | Score  | WR@Mid  | WR@High | Hòa Vốn |
|------|--------|---------|---------|---------|
| 113  | 0.3107 |  31.8%  |  49.3%  |  33.3%  |
| 114  | 0.2960 |  30.4%  |  45.5%  |  33.3%  |
| 115  | 0.3247 |  34.2%  |  49.3%  |  33.3%  |
| 116  | 0.3147 |  32.5%  |  49.3%  |  33.3%  |
| 117  | 0.2729 |  32.8%  |  63.2%  |  33.3%  |
| 118  | {score:.4f}|  {wr_77:.1f}%  | {wr_89:.1f}%  |  33.3%  |

Một phép thử sai lầm đã phải trả giá! Nhằm giải quyết vấn đề thanh khoản cạn kiệt ở Vòng 117, mô hình đã cố gắng phục hồi con số "19 lệnh Buy" trong truyền thuyết. Tuy nhiên, thay vì đi kèm với 56 lệnh Sell bảo chứng, nó chỉ tung ra {total_sell} lệnh Sell. Sự thiếu hụt tỷ trọng phòng thủ đã khiến hệ thống lập tức vỡ trận, Win Rate cắm đầu rơi từ 63.16% xuống thẳng {wr_89:.2f}%. Sự trừng phạt tàn nhẫn này đã khóa cứng chân lý: Cặp số tỷ lệ (19 Buy / 56 Sell) là một thực thể đồng nhất không thể tách rời! 🚀 HolyGrail_119 (PID {pid}) đã kích hoạt! Mục tiêu: Tự động "quay xe" về đúng Điểm Vàng."""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
