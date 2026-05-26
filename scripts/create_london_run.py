import os
import json

base_config_path = 'bot_config_v6_ltc.json'
run_id = 'run_20260518_101000_v6_LONDON_TripleAsset_Seed123'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)

with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['HF_RUN_ID'] = run_id
config['RUN_ID'] = run_id

# Update MTF_INPUTS
mtf_inputs = [
    {
        "SYMBOL": "LTCUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]
    },
    {
        "SYMBOL": "BTCUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": ["log_return_close", "body_pct", "rsi_14_scaled"]
    },
    {
        "SYMBOL": "ETHUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": ["log_return_close", "body_pct", "rsi_14_scaled"]
    }
]
config['FEATURE_ENGINEERING']['MTF_INPUTS'] = mtf_inputs
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.008
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
config['TRAINING']['LEARNING_RATE'] = 5e-5
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['D_MODEL'] = 128
config['TRAINING']['NUM_LAYERS'] = 3
config['TRAINING']['N_HEAD'] = 8

os.makedirs(run_dir, exist_ok=True)
with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created config for {run_id}")
