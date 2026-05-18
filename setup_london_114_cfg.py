import os, json, time, codecs, subprocess as sp, sys

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_BTC5m_Drop15_114'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

diary_entry = f"""
### STATE UPDATE: 2026-05-15 18:25
- **Run ID:** {run_id}
- **Kết quả Triple Leading (BTC+ETH) Seed 113:** THẤT BẠI. Epoch 53 | Score 0.0066 | Val Loss 0.5179. Thêm ETH làm tăng nhiễu và Val Loss xấu đi đáng kể (0.5179 vs 0.4734 của Seed 111). Kết luận: ETH không giúp ích vì tương quan ETH-LTC và BTC-LTC quá tương tự nhau → thêm ETH chỉ là nhân đôi thông tin (information redundancy).
- **Kế hoạch Seed 114 (BTC 5m FastSignal):** Quay về 2 mã (LTC 15m + BTC). Nhưng đổi BTC từ 15m sang 5min với Window 24 để bắt được signal biến động của BTC sớm hơn 10-15 phút so với khung 15m. Giả thuyết: BTC 5m là leading indicator "nhanh nhạy" hơn BTC 15m trong bối cảnh phiên London có breakout mạnh.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_entry)

config = {
    "HF_RUN_ID": run_id,
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT",
    "EXECUTION_SYMBOL": "LTCUSDm",
    "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_LONDON_V6",
    "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.006,
        "SL_PCT": 0.003,
        "MAX_HOLD_BARS": 180,
        "LABEL_MODE": "pct",
        "PIP_SIZE": 0.01,
        "lot_size": 0.1,
        "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {
                "SYMBOL": "LTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 30,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled",
                             "hour_sin", "hour_cos", "volatility_index", "order_flow_imbalance", "atr_14_scaled"]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "5min",     # <<< KEY CHANGE: 15m -> 5m (bắt signal nhanh hơn)
                "WINDOW_SIZE": 24,       # 24 nến 5m = 2 giờ nhìn lại
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "vol_surge_ratio", "rsi_14_scaled"]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True
    },
    "TRAINING": {
        "D_MODEL": 128, "N_HEAD": 8, "NUM_LAYERS": 4,
        "BATCH_SIZE": 256, "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60,
        "LEARNING_RATE": 5e-05, "DROPOUT_RATE": 0.15, "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "workspaces/CFG_LTC_LONDON_V6/data/raw",
        "DATASET_SUFFIX": "2026", "TIMEFRAME": "M1",
        "ROUTING": {"LTCUSDT": "BINANCE", "BTCUSDT": "BINANCE"}
    },
    "LIVE_BOT": {"PAPER_TRADE": True, "TRADE_PLATFORM": "BINANCE", "MAX_ABSOLUTE_MSE": 0.8, "MIN_PROBABILITY_THRESH": 0.59},
    "SESSION": "london",
    "SESSION_UTC": {"START": "07:00", "END": "13:00"},
    "RUN_ID": run_id
}
config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print(f"Config: {config_path}")
print(f"RunID: {run_id}")
