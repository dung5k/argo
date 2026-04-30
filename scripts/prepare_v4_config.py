import json
import os

base_config_path = 'workspaces/CFG_LTC_LONDON_V3_5/base_config.json'
new_config_path = 'workspaces/CFG_LTC_LONDON_V3_5/runs/run_20260426_223100_v4_ldn_31/config.json'

with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# V4 SMC Modifications
config['WINDOW_SIZE'] = 30

# Training Params
if 'TRAINING' not in config:
    config['TRAINING'] = {}
config['TRAINING']['D_MODEL'] = 32
config['TRAINING']['NUM_LAYERS'] = 1
config['TRAINING']['DROPOUT'] = 0.35
config['TRAINING']['POOLING'] = 'attention'
config['TRAINING']['CLS_HEAD'] = 'simple'
config['TRAINING']['BATCH_SIZE'] = 128  # standard stable batch
config['TRAINING']['LEARNING_RATE'] = 3e-5 # stable LR

# Feature Engineering
if 'FEATURE_ENGINEERING' not in config:
    config['FEATURE_ENGINEERING'] = {}
config['FEATURE_ENGINEERING']['VOL_REGIME'] = True
config['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
config['FEATURE_ENGINEERING']['MTF_WINDOWS'] = [15, 60]

# Macro Features
config['MACRO_FEATURES'] = {
    "BTCUSDT": ["close", "volume", "spread_ret", "relative_strength"],
    "ETHUSDT": ["close", "volume", "spread_ret", "relative_strength"]
}

with open(new_config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print("Config v4 generated successfully!")
