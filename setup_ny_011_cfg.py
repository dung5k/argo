import os
import json
from datetime import datetime

base_cfg_path = "bot_config_v6_ltc_ny.json"
with open(base_cfg_path, "r", encoding="utf-8") as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_NY_Triple5m_Win180_011"
run_dir = os.path.join("workspaces", "CFG_LTC_NY_V6", "runs", run_id)
os.makedirs(os.path.join(run_dir, "data", "tensors"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)

# Apply Search Space for Seed 011
config["TRAINING"]["LEARNING_RATE"] = 1.5e-5
config["TRAINING"]["DROPOUT_RATE"] = 0.30
config["TRAINING"]["WARMUP_EPOCHS"] = 15
config["TRAINING"]["BATCH_SIZE"] = 32

config["FEATURE_ENGINEERING"]["TP_PCT"] = 0.005
config["FEATURE_ENGINEERING"]["SL_PCT"] = 0.003
config["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"] = 180

# MTF_INPUTS: LTCUSDT 5min (W180) + BTCUSDT 5min (W180) + ETHUSDT 5min (W180)
config["FEATURE_ENGINEERING"]["MTF_INPUTS"] = [
    {
        "SYMBOL": "LTCUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": [
            "log_return_close",
            "body_pct",
            "bb_width",
            "rsi_14_scaled",
            "hour_sin",
            "hour_cos"
        ]
    },
    {
        "SYMBOL": "BTCUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": [
            "log_return_close",
            "body_pct",
            "rsi_14_scaled"
        ]
    },
    {
        "SYMBOL": "ETHUSDT",
        "TIMEFRAME": "5min",
        "WINDOW_SIZE": 180,
        "FEATURES": [
            "log_return_close",
            "body_pct",
            "rsi_14_scaled"
        ]
    }
]

config_out_path = os.path.join(run_dir, "config.json")
with open(config_out_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)

print(run_id)
