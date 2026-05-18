import os, json
from datetime import datetime

base_cfg_path = r'workspaces\CFG_XAG_LONDON_V5\runs\run_20260516_060355_v5_london_balanced_refiner\config.json'
if not os.path.exists(base_cfg_path):
    base_cfg_path = r'data\bot_config_xag_london_v5.json'

with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

run_id_val = datetime.now().strftime('%Y%m%d_%H%M%S')
run_id = f"run_{run_id_val}_v5_london_gold_anchor"
run_dir = os.path.join('workspaces', 'CFG_XAG_LONDON_V5', 'runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)

config['TRAINING']['LEARNING_RATE'] = 2.0e-5
config['TRAINING']['D_MODEL'] = 128
config['TRAINING']['N_HEAD'] = 8
config['TRAINING']['NUM_LAYERS'] = 3
config['TRAINING']['BATCH_SIZE'] = 64
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['LABEL_SMOOTHING'] = 0.15

config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0035
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0035
config['FEATURE_ENGINEERING']['FAST_HIT_BARS'] = 8

macs = config['FEATURE_ENGINEERING'].get('MACRO_FEATURES', {})
config['FEATURE_ENGINEERING']['MACRO_FEATURES'] = {k: v for k, v in macs.items() if 'XAU' in k}

config['RUN_ID'] = run_id
config['HF_RUN_ID'] = run_id

config_out_path = os.path.join(run_dir, 'config.json')
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(run_id)
