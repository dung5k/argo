import os
import json
from datetime import datetime

base_cfg_path = r'workspaces\CFG_LTC_LONDON_V6\runs\run_20260510_181835_v6_london_win60\config.json'
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_LONDON_Seed123_Refined"
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)

# SỬA SIÊU THAM SỐ CHỐNG OVERFITTING (REGULARIZATION ENHANCEMENT)
config['TRAINING']['LEARNING_RATE'] = 3.0e-5
config['TRAINING']['DROPOUT'] = 0.15
config['TRAINING']['DROPOUT_RATE'] = 0.15
config['TRAINING']['BATCH_SIZE'] = 256
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['FINETUNE_EPOCHS'] = 80
config['TRAINING']['ES_PATIENCE'] = 25  # Tăng khả năng chịu đựng cho Early Stopping

# Bật kiến trúc nâng cao
config['TRAINING']['POOLING'] = 'attention'
config['TRAINING']['CLS_HEAD'] = 'residual'

config['RUN_ID'] = run_id
config['HF_RUN_ID'] = run_id

config_out_path = os.path.join(run_dir, 'config.json')
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(run_id)
