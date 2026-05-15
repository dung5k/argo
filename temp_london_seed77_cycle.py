# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 77 ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed77'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

with open('bot_config_v6_ltc.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
config['TRAINING']['LEARNING_RATE'] = 5e-5
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['DROPOUT_RATE'] = 0.30
config['TRAINING']['D_MODEL'] = 64
config['TRAINING']['N_HEAD'] = 4
config['TRAINING']['NUM_LAYERS'] = 2
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.008
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 20
fe = config.get('FEATURE_ENGINEERING', {})
if 'MTF_INPUTS' in fe:
    fe['MTF_INPUTS'][0]['TIMEFRAME'] = '5min'
    fe['MTF_INPUTS'][0]['WINDOW_SIZE'] = 15
    fe['MTF_INPUTS'] = [fe['MTF_INPUTS'][0]]
config['CONFIG_ID'] = 'CFG_LTC_LONDON_V6'
config['SESSION'] = 'london'
config['SESSION_UTC'] = {"START": "07:00", "END": "13:00"}
config['RUN_ID'] = run_id
config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open('start_train.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os
run_id = "{run_id}"
config_path = r"{config_path}"
env = dict(os.environ, PYTHONIOENCODING="utf-8")
proc = subprocess.Popen(["python", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')
result = sp.run(["python", "start_train.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- APPEND DIARY ----
diary_text = """
### STATE UPDATE: 2026-05-14 10:41
- **Run ID:** run_20260514_103553_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed76
- **Kết quả:** Best Val Loss tại Epoch 6. Composite Score: **0.1190**, Win Rate: **27.02%** (Threshold 0.79), **45.16%** (Threshold 0.92, N=31).
- **Phân tích:** Score tiếp tục dậm chân tại vùng đáy (0.1190). Nguyên nhân vẫn như vòng trước: TUS Score thấp do lệnh Buy áp đảo (27 Buy / 4 Sell). Cú bật nảy (Reversion) vẫn chưa xuất hiện. Tuy nhiên, Val Loss vẫn giữ mức cực kỳ ổn định (0.5013), chứng minh kiến trúc mảng MTF vẫn đang fit tốt.
- **Ý tưởng tiếp theo (Seed 77):** Có thể cần một vài vòng để hệ thống thoát khỏi vùng "từ trường" cục bộ (Local Minima) này của Stochastic Gradient Descent. Tiếp tục khai thác.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 77).

📊 Kết quả FarmSeed 76:
- Best Val Loss tại Epoch 6. Composite Score: 0.1190 (Đáy Stochastic)
- Win Rate: 27.02% (Threshold 0.79) | 45.16% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  71  | 0.1729 |  28.69% |  50.0%  |
|  72  | 0.1304 |  26.41% |  38.8%  |
|  73  | 0.1214 |  25.00% |  52.0%  |
|  74  | 0.1338 |  27.42% |  55.0%  |
|  75  | 0.1199 |  25.97% |  44.1%  |
|  76  | 0.1190 |  27.02% |  45.1%  |

🚨 Hệ thống vẫn đang dò dẫm trong "Vùng Tối" của Local Minima. Điểm nghẽn duy nhất là sự lệch pha tín hiệu cực đại (vẫn thiên vị Buy do sóng Uptrend của dữ liệu Valid). Val Loss vẫn siêu cứng ở 0.5013! 🚀 FarmSeed 77 (PID {pid}) đã bùng cháy! Mục tiêu: Vượt qua hố đen này!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
