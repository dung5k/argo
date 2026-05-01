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

# VÒNG 4: Phân tích lịch sử:
# R1: TP50/SL50, D32, WIN15 → WR 46.7%
# R2: TP40/SL60, D64, WIN15 → WR 57.8% ← BEST
# R3: TP30/SL70, D64, N_HEAD4, WIN15 → WR 35.6% ← QUÁ CỰC ĐOAN
# Historical Run 30: D16, TP80/SL80, WIN20 → Score 0.626 (KHÔNG có ZERO_NOISE/ORDER_FLOW/VOL_REGIME)
#
# Kết luận: TP/SL=40/60 là tối ưu. D_MODEL=64 tốt.
# Giả thuyết mới: USTECm (Nasdaq) là NHIỄU cho XAG NY (training_report.md đã xác nhận).
# → Loại bỏ hoàn toàn USTECm, chỉ giữ XAUUSDm + DXYm (2 leader thực sự).
# → Tăng WINDOW_SIZE lên 20 (mốc lịch sử tối ưu).

cfg['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True
cfg['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
cfg['FEATURE_ENGINEERING']['VOL_REGIME'] = True
cfg['FEATURE_ENGINEERING']['TP_PIPS'] = 40
cfg['FEATURE_ENGINEERING']['SL_PIPS'] = 60
cfg['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 20

# Loại bỏ USTECm (Nasdaq) - nguồn nhiễu đã được xác nhận
cfg['FEATURE_ENGINEERING']['MACRO_FEATURES'] = {
    "XAUUSDm": ["log_ret", "volume", "bb_width", "corr_60", "spread_ret", "dxy_xau_anomaly"],
    "DXYm": ["log_ret", "volume", "bb_width", "corr_60", "spread_ret"]
}

# Cập nhật DATA_SOURCE.ROUTING để không cào USTECm nữa
cfg['DATA_SOURCE']['ROUTING'] = {
    "XAGUSDm": "EXNESS",
    "XAUUSDm": "EXNESS",
    "DXYm": "EXNESS"
}

cfg['TRAINING']['D_MODEL'] = 64
cfg['TRAINING']['N_HEAD'] = 2
cfg['TRAINING']['NUM_LAYERS'] = 1

config_str = json.dumps(cfg['FEATURE_ENGINEERING'], sort_keys=True) + json.dumps(cfg['TRAINING'], sort_keys=True)
config_hash = hashlib.md5(config_str.encode()).hexdigest()

if config_hash in tried_configs:
    print('CONFIG ALREADY TRIED!')
else:
    tried_configs.append(config_hash)
    with open(tried_file, 'w', encoding='utf-8') as f:
        json.dump(tried_configs, f, indent=4)
    
    run_id = f'run_{datetime.now().strftime("%Y%m%d_%H%M%S")}_v3_ny_auto_4'
    run_dir = f'{root_dir}/runs/{run_id}'
    os.makedirs(run_dir, exist_ok=True)
    with open(f'{run_dir}/config.json', 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=4)
    print(run_id)
