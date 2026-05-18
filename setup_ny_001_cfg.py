import os, json, time, codecs

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_NY_15m_W60_Drop10_001'
run_dir = os.path.join('workspaces', 'CFG_LTC_NY_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

diary_entry = f"""
## [Seed 001 - V6 MTF] - Ngày {time.strftime('%Y-%m-%d')}
### Khởi động kỷ nguyên V6 MTF cho phiên New York

- **Run ID:** {run_id}
- **Bối cảnh:** Chuyển từ kiến trúc V3 (single-encoder) sang V6 MTF (multi-encoder). Kế thừa insight vàng từ lịch sử V3: Window 60 nến (1 giờ) và Dropout 0.10 là tổ hợp tốt nhất cho phiên NY. Giữ TP 0.5%/SL 0.3% (R:R 1:1.67) — đây là ngưỡng tối ưu đã được chứng minh (WR 97.06%).
- **Chiến lược Seed 001:** Single TF baseline — LTC 15m với Window 60, Dropout 0.10. Đây là thí nghiệm A/B Testing nền tảng để đo lường xem kiến trúc V6 có duy trì được WR cao như V3 không.
- **Mục tiêu:** Score > 0.50, WR > 70% tại ngưỡng confidence cao.
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
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
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
                "WINDOW_SIZE": 60,   # Kế thừa insight vàng từ V3 (WR 97.06%)
                "FEATURES": [
                    "log_return_close", "body_pct", "bb_width", "rsi_14_scaled",
                    "hour_sin", "hour_cos", "volatility_index", "order_flow_imbalance", "atr_14_scaled"
                ]
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
        "DROPOUT_RATE": 0.10,   # Kế thừa Dropout tốt nhất từ V3
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
