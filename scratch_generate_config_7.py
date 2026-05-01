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

# VÒNG 7: Tổng hợp 6 vòng:
# R2 (WR 57.8%) là CỰC HẠN cho: D64, TP40/SL60, WIN15, LAYERS1, LR1e-5
# Thay đổi kiến trúc, LR, loại features → đều kém hơn.
#
# Chiều không gian chưa khám phá: MAX_HOLD_BARS!
# R2 dùng MAX_HOLD_BARS=12 (kế thừa base_config).
# Giả thuyết: Tại phiên NY hỗn loạn, 12 bars (12 phút) quá ngắn.
# Lệnh chưa kịp chạm TP 40 pips đã bị timeout → tính là thua.
# → Tăng MAX_HOLD_BARS lên 24 (24 phút) để cho lệnh nhiều thời gian hơn.
# → Đồng thời thử tăng nhẹ STEP_SIZE lên 2 (giảm overlap, tăng tính đa dạng dữ liệu)

cfg['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True
cfg['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
cfg['FEATURE_ENGINEERING']['VOL_REGIME'] = True
cfg['FEATURE_ENGINEERING']['TP_PIPS'] = 40
cfg['FEATURE_ENGINEERING']['SL_PIPS'] = 60
cfg['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 15
cfg['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 24
cfg['FEATURE_ENGINEERING']['STEP_SIZE'] = 2

cfg['TRAINING']['D_MODEL'] = 64
cfg['TRAINING']['N_HEAD'] = 2
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
    
    run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_auto_7'
    run_dir = f'{root_dir}/runs/{run_id}'
    os.makedirs(run_dir, exist_ok=True)
    with open(f'{run_dir}/config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(run_id)
