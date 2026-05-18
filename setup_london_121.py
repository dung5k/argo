import os, json
from datetime import datetime

base_cfg_path = r'workspaces\CFG_LTC_LONDON_V6\runs\run_20260517_211958_v6_LONDON_Cross5m_Win180_116\config.json'
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_LONDON_Cross5m_Seed121"
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)

config['TRAINING']['LEARNING_RATE'] = 1.5e-5
config['TRAINING']['DROPOUT_RATE'] = 0.30
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['BATCH_SIZE'] = 64

# Keep the features intact exactly as in Seed 116
config['RUN_ID'] = run_id
config['HF_RUN_ID'] = run_id

config_out_path = os.path.join(run_dir, 'config.json')
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(run_id)
