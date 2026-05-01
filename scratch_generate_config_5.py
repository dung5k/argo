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

# VÒNG 5: Phân tích gradient qua 4 vòng:
# R1: TP50/SL50, D32, WIN15, XAU+USTEC+DXY → WR 46.7%
# R2: TP40/SL60, D64, WIN15, XAU+USTEC+DXY → WR 57.8% ← BEST
# R3: TP30/SL70, D64, WIN15, XAU+USTEC+DXY → WR 35.6% (quá cực đoan)
# R4: TP40/SL60, D64, WIN20, XAU+DXY only  → WR 33.0% (mất USTECm = mất info)
#
# Kết luận rõ ràng:
# 1. TP/SL=40/60 là tối ưu (R2 chứng minh).
# 2. D_MODEL=64 là tối ưu.
# 3. USTECm PHẢI GIỮ (R4 chứng minh loại bỏ là thảm họa).
# 4. WINDOW_SIZE=15 tốt hơn 20.
#
# Chiến thuật Vòng 5: Giữ nguyên combo R2 (tốt nhất), nhưng:
# - Thu nhỏ WINDOW_SIZE xuống 10 (ngắn hơn → bắt sóng nhanh hơn)
# - Tăng NUM_LAYERS lên 2 (thêm sâu → học pattern phức tạp hơn)
# - Tăng DROPOUT lên 0.3 (chống overfit mạnh hơn)

cfg['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True
cfg['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
cfg['FEATURE_ENGINEERING']['VOL_REGIME'] = True
cfg['FEATURE_ENGINEERING']['TP_PIPS'] = 40
cfg['FEATURE_ENGINEERING']['SL_PIPS'] = 60
cfg['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 10

cfg['TRAINING']['D_MODEL'] = 64
cfg['TRAINING']['N_HEAD'] = 2
cfg['TRAINING']['NUM_LAYERS'] = 2
cfg['TRAINING']['DROPOUT'] = 0.3

config_str = json.dumps(cfg['FEATURE_ENGINEERING'], sort_keys=True) + json.dumps(cfg['TRAINING'], sort_keys=True)
config_hash = hashlib.md5(config_str.encode()).hexdigest()

if config_hash in tried_configs:
    print('CONFIG ALREADY TRIED!')
else:
    tried_configs.append(config_hash)
    with open(tried_file, 'w', encoding='utf-8') as f:
        json.dump(tried_configs, f, indent=4)
    
    run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_auto_5'
    run_dir = f'{root_dir}/runs/{run_id}'
    os.makedirs(run_dir, exist_ok=True)
    with open(f'{run_dir}/config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(run_id)
