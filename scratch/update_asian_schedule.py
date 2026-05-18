import json

with open("bot_schedule_v6_ltc.json", "r", encoding="utf-8") as f:
    data = json.load(f)

data["schedule"]["asian"] = {
    "start": "23:00",
    "end": "07:00",
    "run_id": "run_20260515_152956_v6_ASIAN_5m_CapacityScaling_211",
    "config_id": "CFG_LTC_ASIAN_V6",
    "dataset_repo": "dung5k/argo_workspaces",
    "trading_config": {
        "min_prob_thresh": 0.74,
        "mse_thresh_perc": 70.0
    },
    "feature_engineering": {
        "TP_PCT": 0.003,
        "SL_PCT": 0.0025,
        "MAX_HOLD_BARS": 24,
        "FAST_HIT_BARS": 5,
        "LABEL_MODE": "pct",
        "PIP_SIZE": 0.01,
        "lot_size": 0.1,
        "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {
                "SYMBOL": "LTCUSDT",
                "TIMEFRAME": "5min",
                "WINDOW_SIZE": 24,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos", "delta_volume", "vol_surge_ratio"]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 8,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]
            },
            {
                "SYMBOL": "ETHUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 8,
                "FEATURES": ["log_return_close", "body_pct"]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True,
        "STEP_SIZE": 1
    },
    "training": {
        "D_MODEL": 64,
        "N_HEAD": 8,
        "NUM_LAYERS": 3,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 80,
        "LEARNING_RATE": 1e-05,
        "DROPOUT_RATE": 0.2,
        "LR_SCHEDULER": "cosine_warm",
        "POOLING": "attention"
    }
}

with open("bot_schedule_v6_ltc.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
