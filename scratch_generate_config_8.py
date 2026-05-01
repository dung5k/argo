import json
import os
from datetime import datetime
import hashlib

root_dir = 'workspaces/CFG_XAG_NY_V3_5'
tried_file = f'{root_dir}/ny_tried_configs.json'

with open(tried_file, 'r', encoding='utf-8') as f:
    tried_configs = json.load(f)

with open(f'{root_dir}/base_config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# VÒNG 8: Tổng hợp 7 vòng — R2 là CỰC HẠN bất khả xâm phạm.
# Mọi chiều không gian đã khám phá đều kém hơn R2:
#   TP/SL, D_MODEL, LAYERS, WIN, MACRO, LR, MAX_HOLD, STEP
#
# Chiến thuật mới: Thử D_MODEL=48 (điểm giữa D32=46.7% và D64=57.8%)
# Kết hợp N_HEAD=4 (nhiều attention hơn cho model vừa phải)
# Giữ nguyên mọi thứ khác từ R2 (TP40/SL60, WIN15, LAYERS1, LR1e-5)

cfg['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True
cfg['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
cfg['FEATURE_ENGINEERING']['VOL_REGIME'] = True
cfg['FEATURE_ENGINEERING']['TP_PIPS'] = 40
cfg['FEATURE_ENGINEERING']['SL_PIPS'] = 60
cfg['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 15

cfg['TRAINING']['D_MODEL'] = 48
cfg['TRAINING']['N_HEAD'] = 4  # 48/4 = 12 dim per head
cfg['TRAINING']['NUM_LAYERS'] = 1
cfg['TRAINING']['DROPOUT'] = 0.25
cfg['TRAINING']['LEARNING_RATE'] = 1e-5

config_str = json.dumps(cfg['FEATURE_ENGINEERING'], sort_keys=True) + json.dumps(cfg['TRAINING'], sort_keys=True)
config_hash = hashlib.md5(config_str.encode()).hexdigest()

if config_hash in tried_configs:
    print('CONFIG ALREADY TRIED!')
else:
    tried_configs.append(config_hash)
    with open(tried_file, 'w', encoding='utf-8') as f:
        json.dump(tried_configs, f, indent=4)
    
    run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_auto_8'
    run_dir = f'{root_dir}/runs/{run_id}'
    os.makedirs(run_dir, exist_ok=True)
    with open(f'{run_dir}/config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(run_id)
