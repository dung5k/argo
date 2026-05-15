# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 105 (FIX MAX_HOLD_BARS) ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_TP8_SL3_Drop30_W30_FarmSeed105'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

with open('workspaces/CFG_LTC_LONDON_V6/runs/run_20260514_135331_v6_LONDON_15m_TP8_SL3_Drop30_W30_FarmSeed104/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# FIX MAX_HOLD_BARS
# Trước đó đặt = 12 nhưng quên mất Base TF là 1m, nên Bot chỉ gồng 12 phút! Quá ngắn để ăn 0.8%.
# Đổi thành 180 (3 tiếng) để phù hợp với chiến lược khung 15m.
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 180

config['RUN_ID'] = run_id
config_path = os.path.join(run_dir, 'config.json')

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open('start_train.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id}"
config_path = r"{config_path}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Generating new dataset tensors...")
with open("upload_v6.log", "w", encoding="utf-8") as f_log:
    sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", config_path, "--no-upload"], env=env, stdout=f_log, stderr=subprocess.STDOUT)
if sp1.returncode != 0:
    print("Error generating dataset, check upload_v6.log")
    sys.exit(1)
print("Dataset generation completed. Starting training...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')
result = sp.run(["python", "start_train.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- APPEND DIARY ----
diary_text = """
### STATE UPDATE: 2026-05-14 14:12
- **Run ID:** run_20260514_135331_v6_LONDON_15m_TP8_SL3_Drop30_W30_FarmSeed104
- **Kết quả:** Best Val Loss tại Epoch 62. Composite Score: **0.0591**, Win Rate: **7.18%** (Threshold 0.78), **17.94%** (Threshold 0.91, N=39).
- **Phân tích:** Cú Pivot "Đập đi xây lại" (não to 128, khung 15m) đã gặp một CÚ SỐC CÔNG NGHỆ! Win Rate sụp đổ hoàn toàn về mức 17%, Val Loss tăng vọt lên 0.5319. Nguyên nhân gốc rễ đã được tìm ra: Trong lúc tối ưu "Fast Hit", chúng ta đã giảm `MAX_HOLD_BARS` xuống 12. Tuy nhiên, base nến vẫn là 1 phút, nghĩa là mô hình **chỉ được phép gồng lệnh trong đúng 12 phút**! Việc giá LTC chạy 0.8% trong 12 phút là điều hoang tưởng.
- **Ý tưởng tiếp theo (Seed 105 - Vá Lỗi):** Giữ nguyên kiến trúc não to của Seed 104, nhưng điều chỉnh lại `MAX_HOLD_BARS = 180` (tương đương 3 tiếng) để phù hợp với khung nhìn 15 phút. Model cần đủ thời gian thở để giá di chuyển tới điểm Take Profit. Bắt buộc `--scratch` lại tensor.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 105 - Vá Lỗi Cấu Trúc).

📊 Kết quả FarmSeed 104:
- Best Val Loss tại Epoch 62. Composite Score: 0.0591
- Win Rate: 7.18% (Threshold 0.78) | 17.94% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (15m_W30_Drop30_LR5e-5_L4):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  99  | 0.0920 |  22.18% |  50.0%  |
| 100  | 0.0928 |  23.48% |  46.8%  |
| 101  | 0.0977 |  23.00% |  46.6%  |
| 102  | 0.0981 |  24.01% |  47.3%  |
| 103  | 0.0922 |  22.77% |  45.4%  |
| 104  | 0.0591 |   7.18% |  17.9%  |

🚨 CÚ NGÃ CỦA "NÃO TO" VÀ BÀI HỌC VỀ LOGIC: 
Seed 104 đã sụp đổ thảm hại (WR 17%)! Val Loss tăng lên 0.5319. Nguyên nhân không phải do mạng Neural dở, mà do **lỗi cài đặt Logic** của kỹ sư: 
Để ép mô hình "Fast Hit", chúng ta đã giảm `MAX_HOLD_BARS` xuống 12. Nhưng base nến là 1 phút, tức là Bot bị ép phải chốt lãi 0.8% **chỉ trong vỏn vẹn 12 phút**! Hầu hết các lệnh đều bị Timeout và đánh trượt.

🔥 Seed 105 sẽ vá ngay lỗ hổng này: 
- Nới lỏng `MAX_HOLD_BARS = 180` (Gồng 3 tiếng, cực kỳ phù hợp với góc nhìn 15m).
- Giữ nguyên sức mạnh mạng (D128, H8, L4).
🚀 FarmSeed 105 (PID {pid}) đã bùng cháy! Mục tiêu: Lấy lại phong độ Val Loss < 0.50!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
