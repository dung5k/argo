import os, json
from datetime import datetime

base_cfg_path = r'workspaces\CFG_LTC_LONDON_V6\runs\run_20260517_211958_v6_LONDON_Cross5m_Win180_116\config.json'
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_LONDON_Cross5m_Seed117"
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)

config['TRAINING']['LEARNING_RATE'] = 2.5e-5
config['TRAINING']['DROPOUT_RATE'] = 0.25
config['TRAINING']['WARMUP_EPOCHS'] = 12
config['TRAINING']['BATCH_SIZE'] = 64

config['FEATURE_ENGINEERING']['TP_PCT'] = 0.006
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 144

if 'ETHUSDT' not in config['DATA_SOURCE']['ROUTING']:
    config['DATA_SOURCE']['ROUTING']['ETHUSDT'] = 'BINANCE'

config['FEATURE_ENGINEERING']['MTF_INPUTS'] = [
    {
        'SYMBOL': 'LTCUSDT',
        'TIMEFRAME': '5min',
        'WINDOW_SIZE': 180,
        'FEATURES': ['log_return_close', 'body_pct', 'bb_width', 'rsi_14_scaled', 'hour_sin', 'hour_cos']
    },
    {
        'SYMBOL': 'BTCUSDT',
        'TIMEFRAME': '5min',
        'WINDOW_SIZE': 180,
        'FEATURES': ['log_return_close', 'body_pct', 'rsi_14_scaled']
    },
    {
        'SYMBOL': 'ETHUSDT',
        'TIMEFRAME': '5min',
        'WINDOW_SIZE': 180,
        'FEATURES': ['log_return_close', 'body_pct', 'rsi_14_scaled']
    }
]

config['RUN_ID'] = run_id
config['HF_RUN_ID'] = run_id

config_out_path = os.path.join(run_dir, 'config.json')
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(run_id)
