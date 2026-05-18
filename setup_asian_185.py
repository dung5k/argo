# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 184 (LeadBTC1m_D64_184):
- **Kết quả:** Hội tụ tại Epoch 2. Composite Score: 0.3512. Win Rate đỉnh: **56.25%** (Threshold 0.94).
- **Cấu hình:** LTC 1min (W20) + BTC 1min (W20) + D_MODEL=64.
- **Phân tích:** Việc đồng bộ Timeframe (cùng là 1min) đã giúp Win Rate nhích lên 56.25%, là mức cao nhất từ khi áp dụng Leading Indicator Strategy, nhưng vẫn chưa qua màng lọc 60%. Khung 1 phút có thể quá nhiễu khi kết hợp 2 symbol, khiến bộ não bị "ngợp" thông tin vi mô.

### Ý tưởng tiếp theo (Vòng 185 - LeadBTC5m_Base5m_185):
- **Hành động:** Chuyển Base Timeframe của LTC sang **5min** và dùng BTC **5min** làm Leading Indicator. Điều chỉnh TP lên 0.35% và SL 0.2% cho phù hợp khung 5 phút.
- **Giả thuyết:** Nâng lên khung 5 phút sẽ lọc bỏ bớt nhiễu vi mô của khung 1 phút, giúp tín hiệu dẫn dắt của BTC rõ nét và ổn định hơn.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_LeadBTC5m_D64_185'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": "run_20260511_210003_v3",
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT", "EXECUTION_SYMBOL": "LTCUSDm", "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_ASIAN_V6", "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.0035, "SL_PCT": 0.002, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 64, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 2e-05,
                 "DROPOUT_RATE": 0.25, "LR_SCHEDULER": "cosine_warm"},
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {"RAW_LOCAL_DIR": "data/history", "DATASET_SUFFIX": "2026", "TIMEFRAME": "M1",
                    "ROUTING": {"LTCUSDT": "BINANCE", "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE"}},
    "LIVE_BOT": {"PAPER_TRADE": True, "TRADE_PLATFORM": "BINANCE", "MAX_ABSOLUTE_MSE": 0.8, "MIN_PROBABILITY_THRESH": 0.59},
    "SESSION": "asian", "SESSION_UTC": {"START": "23:00", "END": "07:00"}, "RUN_ID": run_id
}

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

starter = f'''import subprocess, os, sys
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_185.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_185.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC5m_Base5m_185).

📊 Kết quả V184 (LTC 1m + BTC 1m + D_MODEL 64):
- Best Val Loss tại Epoch 2. Composite Score: 0.3512
- Win Rate: 56.25% (Threshold 0.94) | 49.75% (Threshold 0.80)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 179  | LTC 5m + 15m (Dual)   | 0.00%  | 0.0000 |
| 180  | LTC 1m + BTC 15m (D32)| 43.90% | 0.3140 |
| 181  | LTC 1m + BTC 5m (D32) | 47.26% | 0.3367 |
| 182  | LTC 1m + ETH 5m (D32) | 45.33% | 0.3427 |
| 183  | LTC 1m + BTC 5m (D64) | 54.72% | 0.3584 |
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |

Nhận định: Đồng bộ Timeframe 1 phút đã giúp WR lên mức cao nhất (56.25%) trong chuỗi Leading Indicator, nhưng nhiễu (noise) trên khung 1m vẫn quá lớn khi kết hợp 2 mã.

🎯 Ý tưởng mới (Vòng 185): Nâng Base Timeframe lên 5 phút!
- Chuyển LTCUSDT sang khung 5min (W20).
- Dùng BTCUSDT 5min (W20) làm Leading Indicator.
- Tăng TP lên 0.35%, SL 0.2% (phù hợp sóng 5m).
- Giả thuyết: Khung 5 phút sẽ lọc nhiễu, giúp mô hình bắt được xu hướng dẫn dắt của BTC rõ ràng hơn.

🚀 LeadBTC5m_Base5m_185 (PID {pid}) đã kích hoạt! Mục tiêu: Vượt mốc 60% WR!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
