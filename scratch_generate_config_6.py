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

# VÒNG 6: Phân tích gradient qua 5 vòng:
# R2 là ĐỈNH TUYỆT ĐỐI: TP40/SL60, D64, WIN15, LAYERS=1, LR=1e-5 → WR 57.8%
# Mọi thay đổi kiến trúc đều kéo xuống.
# 
# Giả thuyết: R2 đang bị mắc kẹt ở Local Minima.
# → Giữ NGUYÊN HOÀN TOÀN kiến trúc R2, chỉ tăng LR từ 1e-5 lên 5e-5
#   để optimizer nhảy xa hơn và có thể tìm Global Minima.

cfg['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True
cfg['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
cfg['FEATURE_ENGINEERING']['VOL_REGIME'] = True
cfg['FEATURE_ENGINEERING']['TP_PIPS'] = 40
cfg['FEATURE_ENGINEERING']['SL_PIPS'] = 60
cfg['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 15

cfg['TRAINING']['D_MODEL'] = 64
cfg['TRAINING']['N_HEAD'] = 2
cfg['TRAINING']['NUM_LAYERS'] = 1
cfg['TRAINING']['DROPOUT'] = 0.25
cfg['TRAINING']['LEARNING_RATE'] = 5e-5  # Tăng 5x so với R2

config_str = json.dumps(cfg['FEATURE_ENGINEERING'], sort_keys=True) + json.dumps(cfg['TRAINING'], sort_keys=True)
config_hash = hashlib.md5(config_str.encode()).hexdigest()

if config_hash in tried_configs:
    print('CONFIG ALREADY TRIED!')
else:
    tried_configs.append(config_hash)
    with open(tried_file, 'w', encoding='utf-8') as f:
        json.dump(tried_configs, f, indent=4)
    
    run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_auto_6'
    run_dir = f'{root_dir}/runs/{run_id}'
    os.makedirs(run_dir, exist_ok=True)
    with open(f'{run_dir}/config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(run_id)
