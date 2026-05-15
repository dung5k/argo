import json
import os

config_path = r'd:\DungLA\client1\bot_config_v6_ltc_weekend.json'
out_path = r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260510_083200_v6_weekend_continuous_46\config.json'

with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['TRAINING']['BATCH_SIZE'] = 16
config['TRAINING']['LEARNING_RATE'] = 0.0001
config['TRAINING']['D_MODEL'] = 32
config['TRAINING']['DROPOUT_RATE'] = 0.0
config['TRAINING']['NUM_LAYERS'] = 3
config['TRAINING']['FOCAL_GAMMA'] = 0.0
config['TRAINING']['POOLING'] = "mean"
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.005
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003

config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '30min'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 8

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
