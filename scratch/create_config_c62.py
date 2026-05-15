import json
import os

config_path = r'd:\DungLA\client1\bot_config_v6_ltc_weekend.json'
out_path = r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260510_112700_v6_weekend_continuous_62\config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['TRAINING']['BATCH_SIZE'] = 64
config['TRAINING']['LEARNING_RATE'] = 0.00001
config['TRAINING']['D_MODEL'] = 32
config['TRAINING']['DROPOUT_RATE'] = 0.1
config['TRAINING']['NUM_LAYERS'] = 3
config['TRAINING']['FOCAL_GAMMA'] = 0.0
config['TRAINING']['POOLING'] = "mean"
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0025
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.002
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 60

config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1min'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 90
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['FEATURES'] = [
    'log_return_close', 'body_pct', 'delta_volume', 'cum_delta_session', 
    'order_flow_imbalance', 'vol_surge_ratio', 'rsi_5_scaled', 'hour_sin', 'hour_cos'
]

if len(config['FEATURE_ENGINEERING']['MTF_INPUTS']) > 1:
    config['FEATURE_ENGINEERING']['MTF_INPUTS'][1]['FEATURES'] = [
        'log_return_close', 'delta_volume', 'vol_surge_ratio', 'bb_width'
    ]

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
