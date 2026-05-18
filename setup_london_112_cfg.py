import os, json, time, codecs, subprocess as sp, sys

# ============ STATE 0: PHÂN TÍCH SEED 111 ============
# Epoch 82 | Score 0.0077 | WR@0.62=53.8% | WR@0.67=63.3% | N=30 | Val Loss=0.4734
# Val Loss 0.4734 là KỶ LỤC LỊCH SỬ MỚI (thấp hơn cả Seed 108 là 0.4897!)
# Nhưng Composite Score sụt vì: TUS Score cao (0.8-0.95) nhưng tín hiệu N=30 ít quá
# → Vấn đề: Kiến trúc 2 encoder (LTC + BTC) có fusion_dim = 128*2 = 256
#   Classification head với Dropout 0.15 vẫn chưa đủ để khai thác 256 chiều
# → Kế hoạch Seed 112: Tăng TP lên 0.008 (R:R 1:2.67), giữ Dropout 0.15, giữ MTF 2 mã
#   Tỷ lệ Hit Rate sẽ thấp hơn nhưng mỗi lần thắng lớn hơn → kỳ vọng composite score tăng

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_BTC_Drop15_TP8_112'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

# ============ CẬP NHẬT DIARY ============
diary_entry = f"""
### STATE UPDATE: 2026-05-15 17:46
- **Run ID:** {run_id}
- **Kết quả BTC_Drop15 Seed 111:** Epoch 82 | Score 0.0077 | Val Loss 0.4734 (KỶ LỤC LỊCH SỬ MỚI!) | WR@0.62=53.8% | WR@0.67=63.3% | N=30
- **Phân tích đột phá:** Val Loss 0.4734 thấp nhất từ trước đến nay, vượt qua cả Seed 108 (0.4897). Điều này chứng tỏ kiến trúc MTF 2 mã (LTC + BTC) + Dropout 0.15 đang HỌC RẤT TỐT về cấu trúc thị trường. Vấn đề nằm ở Composite Score thấp do cách tính: mặc dù WR@0.67=63.3%, nhưng TP 0.6% tạo ra tỷ lệ R:R chỉ 1:2 và EV_Score bị giới hạn.
- **Kế hoạch Seed 112 (TP Boost):** Tận dụng kiến trúc đang hoạt động tốt (2 mã MTF + Dropout 0.15). Nâng TP từ 0.006 lên 0.008 (R:R 1:2.67, Breakeven = SL/(TP+SL) = 0.3/(0.8+0.3) = 27.3%). Với WR > 63%, kỳ vọng EV và Composite Score sẽ bùng nổ.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_entry)

# ============ TẠO CONFIG SEED 112 ============
config = {
    "HF_RUN_ID": run_id,
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT",
    "EXECUTION_SYMBOL": "LTCUSDm",
    "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_LONDON_V6",
    "VERSION": "6.0",
    "HF_CLOUD": {
        "DATASET_REPO": "dung5k/argo_workspaces",
        "MODEL_REPO": "dung5k/argo_workspaces",
        "SYNC_CHUNKS": True
    },
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.008,      # <<<< KEY CHANGE: 0.006 -> 0.008 (R:R 1:2.67)
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
                "FEATURES": [
                    "log_return_close",
                    "body_pct",
                    "bb_width",
                    "rsi_14_scaled",
                    "hour_sin",
                    "hour_cos",
                    "volatility_index",
                    "order_flow_imbalance",
                    "atr_14_scaled"
                ]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 16,
                "FEATURES": [
                    "log_return_close",
                    "body_pct",
                    "bb_width",
                    "vol_surge_ratio"
                ]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True
    },
    "TRAINING": {
        "D_MODEL": 128,
        "N_HEAD": 8,
        "NUM_LAYERS": 4,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 60,
        "LEARNING_RATE": 5e-05,
        "DROPOUT_RATE": 0.15,
        "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "workspaces/CFG_LTC_LONDON_V6/data/raw",
        "DATASET_SUFFIX": "2026",
        "TIMEFRAME": "M1",
        "ROUTING": {
            "LTCUSDT": "BINANCE",
            "BTCUSDT": "BINANCE"
        }
    },
    "LIVE_BOT": {
        "PAPER_TRADE": True,
        "TRADE_PLATFORM": "BINANCE",
        "MAX_ABSOLUTE_MSE": 0.8,
        "MIN_PROBABILITY_THRESH": 0.59
    },
    "SESSION": "london",
    "SESSION_UTC": {"START": "07:00", "END": "13:00"},
    "RUN_ID": run_id
}
config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print(f"Config created: {config_path}")
print(f"Run ID: {run_id}")
print("READY_FOR_TRAINING")
