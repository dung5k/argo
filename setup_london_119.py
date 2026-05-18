import os, json
from datetime import datetime

base_cfg_path = r'workspaces\CFG_LTC_LONDON_V6\runs\run_20260517_211958_v6_LONDON_Cross5m_Win180_116\config.json'
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_LONDON_Cross15m_Seed119"
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)

config['TRAINING']['LEARNING_RATE'] = 2.0e-5
config['TRAINING']['DROPOUT_RATE'] = 0.20
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['BATCH_SIZE'] = 64

# Larger TP/SL for 15m timeframe (capture larger trends)
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.008
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.004
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 48 # Less bars needed for 15m (12 hours)

# Seed 119: Change Base Timeframe to 15m. Keep BTC and ETH because 15m needs macroeconomic consensus!
mtf_inputs = config['FEATURE_ENGINEERING'].get('MTF_INPUTS', [])
for m in mtf_inputs:
    m['TIMEFRAME'] = '15min'
    m['WINDOW_SIZE'] = 60 # 60 bars of 15m = 15 hours of history
config['FEATURE_ENGINEERING']['MTF_INPUTS'] = mtf_inputs

config['RUN_ID'] = run_id
config['HF_RUN_ID'] = run_id

config_out_path = os.path.join(run_dir, 'config.json')
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(run_id)
