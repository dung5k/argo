# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 81 ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed81'
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
### STATE UPDATE: 2026-05-14 11:10
- **Run ID:** run_20260514_110435_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed80
- **Kết quả:** Best Val Loss tại Epoch 2. Composite Score: **0.1114** (Đáy tuyệt đối mới), Win Rate: **25.51%** (Threshold 0.78), **45.45%** (Threshold 0.91, N=33).
- **Phân tích:** Score tiếp tục rớt xuống đáy mới (0.1114). Tình trạng chung vẫn không đổi: TUS Score phạt quá nặng do lệnh Buy áp đảo (29 Buy / 4 Sell). Win Rate giảm nhẹ xuống 45.45%. Val Loss vẫn ổn định tại 0.5024.
- **Ý tưởng tiếp theo (Seed 81):** Chấp nhận chuỗi giảm này. Thuật toán đang bị kẹt sâu trong Local Minima của phân phối dữ liệu ngẫu nhiên. Tiếp tục Farm Seed 81.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 81).

📊 Kết quả FarmSeed 80:
- Best Val Loss tại Epoch 2. Composite Score: 0.1114 (Đáy tuyệt đối)
- Win Rate: 25.51% (Threshold 0.78) | 45.45% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  75  | 0.1199 |  25.97% |  44.1%  |
|  76  | 0.1190 |  27.02% |  45.1%  |
|  77  | **0.1662** |  26.44% |  54.0%  |
|  78  | 0.1216 |  26.17% |  45.1%  |
|  79  | 0.1168 |  25.03% |  52.8%  |
|  80  | 0.1114 |  25.51% |  45.4%  |

🚨 Score tiếp tục rớt đáy! Val Loss không đổi nhưng Win Rate cực đại giảm nhẹ và lỗi mất cân bằng (thiên vị Buy) vẫn tồn tại. Hệ thống đang kẹt rất sâu trong vùng nhiễu này. 🚀 FarmSeed 81 (PID {pid}) đã bùng cháy! Mục tiêu: Ráng lết qua "vũng lầy" Stochastic!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
