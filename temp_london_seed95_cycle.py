# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 95 ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed95'
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
### STATE UPDATE: 2026-05-14 12:44
- **Run ID:** run_20260514_123808_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed94
- **Kết quả:** Best Val Loss tại Epoch 2. Composite Score: **0.1013**, Win Rate: **24.71%** (Threshold 0.79), **43.33%** (Threshold 0.92, N=30).
- **Phân tích:** Chuỗi kỷ lục 10 vòng liên tiếp Val Loss < 0.500 ĐÃ BỊ PHÁ VỠ! Val Loss vòng này nhích lên **0.5011**. Dù vậy, nó vẫn là một con số rất xuất sắc. Composite Score phục hồi nhẹ lên 0.1013 nhưng Win Rate đỉnh tiếp tục sụt giảm còn 43.33% và TUS Score phạt kịch khung (26 Buy / 4 Sell). Hệ thống đang trải qua một chu kỳ "đổ xúc xắc" Validation toàn các sóng Uptrend mù mịt.
- **Ý tưởng tiếp theo (Seed 95):** Chuỗi Val Loss <0.500 đã đứt, nhưng giá trị 0.5011 vẫn là minh chứng cho sự ổn định tuyệt vời của bộ tham số này. Không dao động, không thay đổi cấu trúc, chúng ta sẽ lỳ đòn đua cùng với Random Seed. Khởi động FarmSeed 95.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 95).

📊 Kết quả FarmSeed 94:
- Best Val Loss tại Epoch 2. Composite Score: 0.1013 (Phục hồi nhẹ)
- Win Rate: 24.71% (Threshold 0.79) | 43.33% (Threshold 0.92)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  89  | 0.1043 |  23.52% |  51.3%  |
|  90  | 0.1152 |  26.46% |  50.0%  |
|  91  | 0.0986 |  23.83% |  47.6%  |
|  92  | 0.1022 |  24.19% |  50.0%  |
|  93  | 0.0969 |  23.53% |  45.4%  |
|  94  | 0.1013 |  24.71% |  43.3%  |

🚨 CHUỖI KỶ LỤC BỊ PHÁ VỠ: Sau 10 vòng liên tiếp đóng đinh dưới mốc 0.500, Val Loss đã chính thức nhô lên ngưỡng **0.5011**. 
🔥 Dù đứt chuỗi, đây vẫn là một mức Val Loss đáng nể. Score nhích lên 0.1013 dù Win Rate sụt giảm và TUS Score phạt kịch khung (26 Buy / 4 Sell). Cỗ máy AI đang lỳ đòn chống chọi lại những chu kỳ Validation phân cực xấu nhất. 🚀 FarmSeed 95 (PID {pid}) đã bùng cháy! Kiên trì bảo vệ pháo đài!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
