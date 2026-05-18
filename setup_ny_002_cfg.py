import os, json, time, codecs

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_NY_15m_BTC5m_Drop10_002'
run_dir = os.path.join('workspaces', 'CFG_LTC_NY_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

diary_entry = f"""
## [Seed 002 - V6 MTF] - Ngày {time.strftime('%Y-%m-%d')}
### Thử nghiệm Chỉ Báo Dẫn Dắt (BTC 5min)

- **Kết quả Seed 001 (LTC15m_W60_Drop10):** Early Stopping tại Epoch 49 (Best Epoch 27). Score 0.0190, WR = 73.5% tại Threshold 0.69. Một khởi đầu cực tốt cho V6!
- **Kế hoạch Seed 002:** Bắt đầu ứng dụng "Leading Indicator Strategy". Phiên New York có độ giật rất mạnh lúc mở cửa (US Market Open / Macro News). BTCUSDT thường phản ứng trước tiên với tin tức. Thêm **BTCUSDT 5min** (Window 30 nến = 2.5 giờ) làm Multi-Timeframe input thứ hai. LTCUSDT giữ nguyên base 15min (Window 60).
- **Mục tiêu:** Kiểm chứng xem nhiễu (whipsaw) có giảm đi nhờ tín hiệu vi mô từ BTC 5min không. Kỳ vọng WR > 75% tại Threshold > 0.70.
"""
with codecs.open('workspaces/CFG_LTC_NY_V6/NY_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_entry)

config = {
    "HF_RUN_ID": run_id,
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT",
    "EXECUTION_SYMBOL": "LTCUSDm",
    "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_NY_V6",
    "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": False},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.005,
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
                "WINDOW_SIZE": 60,
                "FEATURES": [
                    "log_return_close", "body_pct", "bb_width", "rsi_14_scaled",
                    "hour_sin", "hour_cos", "volatility_index", "order_flow_imbalance", "atr_14_scaled"
                ]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "5min",
                "WINDOW_SIZE": 30,
                "FEATURES": ["log_return_close", "body_pct", "vol_surge_ratio", "bb_width"]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True
    },
    "TRAINING": {
        "D_MODEL": 128, "N_HEAD": 8, "NUM_LAYERS": 4,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 60,
        "LEARNING_RATE": 5e-05,
        "DROPOUT_RATE": 0.10,
        "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "workspaces/CFG_LTC_NY_V6/data/raw",
        "DATASET_SUFFIX": "2026", "TIMEFRAME": "M1",
        "ROUTING": {"LTCUSDT": "BINANCE", "BTCUSDT": "BINANCE"}
    },
    "LIVE_BOT": {"PAPER_TRADE": True, "TRADE_PLATFORM": "BINANCE", "MAX_ABSOLUTE_MSE": 0.8, "MIN_PROBABILITY_THRESH": 0.59},
    "SESSION": "ny",
    "SESSION_UTC": {"START": "13:00", "END": "21:00"},
    "RUN_ID": run_id
}
with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)
print(f"RunID: {run_id}")
