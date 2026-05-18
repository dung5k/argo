import os, json, time, codecs, subprocess as sp, sys, shutil

# ============ STATE 0: PHÂN TÍCH SEED 112 ============
# Epoch 63 | Score 0.0034 | WR@0.57=38.7% | THẤT BẠI
# TP 0.8% làm label khó → model gặp "Moving target" problem
# Kết luận: TP 0.6% là ngưỡng tối ưu cho khung 15m London
# Hướng mới (Seed 113): Quay về TP 0.6%, Dropout 0.15 giữ nguyên
# NHƯNG mở rộng không gian Input thêm ETH làm leading indicator thứ 3
# BTC → ETH → LTC: Chuỗi dẫn dắt cổ điển trong crypto phiên London

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_BTC_ETH_Drop15_113'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

diary_entry = f"""
### STATE UPDATE: 2026-05-15 18:11
- **Run ID:** {run_id}
- **Kết quả BTC_Drop15_TP8 Seed 112:** THẤT BẠI. Epoch 63 | Score 0.0034 | WR@0.57=38.7%. TP 0.8% tạo nhãn Label quá khó, model không học nổi với chỉ 60 epochs fine-tune. Rõ ràng TP 0.6% là "Sweet Spot" cho khung 15m London.
- **Kế hoạch Seed 113 (Triple Leading Indicator):** Quay về TP 0.6%, Dropout 0.15. Thêm ETHUSDT (5min, Window 24) vào MTF_INPUTS làm leading indicator thứ 3 trong chuỗi dẫn dắt cổ điển: BTC → ETH → LTC. ETH thường di chuyển trước LTC ~2-5 phút và có tương quan chặt hơn BTC trong phiên London. Đây là thử nghiệm cấu trúc MTF 3 mã đầu tiên!
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
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 16,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "vol_surge_ratio"]
            },
            {
                "SYMBOL": "ETHUSDT",      # <<< NEW: ETH leading indicator
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 16,
                "FEATURES": ["log_return_close", "body_pct", "rsi_14_scaled"]
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
        "ROUTING": {"LTCUSDT": "BINANCE", "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE"}
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
