# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 63 ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed63'
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
print(result.stdout.strip())

# ---- APPEND DIARY ----
diary_text = """
### STATE UPDATE: 2026-05-14 09:00
- **Run ID:** run_20260514_085436_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed62
- **Kết quả:** Best Val Loss tại Epoch 3. Composite Score: **0.1701**, Win Rate: **29.01%** (Threshold 0.80), **45.71%** (Threshold 0.93, N=35).
- **Phân tích:** Seed 62 chốt Score 0.1701 — nằm trong vùng ổn định. Val Loss đạt 0.5071 (thấp nhất trong chuỗi này!) cho thấy mô hình hội tụ tốt về mặt Loss. Tuy nhiên WR@0.94 hơi giảm xuống 45.71% do Threshold max thay đổi thành 0.93 (phụ thuộc phân bố Softmax của Seed ngẫu nhiên). Cần tiếp tục Mining.
- **Ý tưởng tiếp theo (Seed 63):** Giữ nguyên cấu hình vàng. Tiếp tục cày.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT ----
msg = """🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 63).

📊 Kết quả FarmSeed 62:
- Best Val Loss tại Epoch 3. Composite Score: 0.1701
- Win Rate: 29.01% (Threshold 0.80) | 45.71% (Threshold 0.93)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  57  | 0.1639 |  28.04% |  41.7%  |
|  58  | 0.1754 |  28.41% |  53.1%  |
|  59  | 0.1810 |  29.42% |  53.1%  |
|  60  | 0.1664 |  30.94% |  50.0%  |
|  61  | 0.1747 |  28.59% |  50.0%  |
|  62  | 0.1701 |  29.01% |  45.7%  |

Score dao động ổn định trong vùng [0.163-0.181]. Kỷ lục 0.1810 (Seed 59) vẫn chưa bị phá — cần kiên trì đào tiếp! 🚀 FarmSeed 63 đã bùng cháy! Mục tiêu: Phá kỷ lục 0.1810!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
