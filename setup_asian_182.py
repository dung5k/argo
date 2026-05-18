# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. APPEND DIARY
diary_text = """
### Tóm tắt Vòng 181 (LeadBTC5m_181):
- **Kết quả:** Hội tụ tại Epoch 2. Composite Score: 0.3367. Win Rate đỉnh: **47.26%** (Threshold 0.72).
- **Cấu hình:** LTC 1min (W20) + BTCUSDT 5min (W20).
- **Phân tích:** BTC 5min cho kết quả tốt hơn BTC 15min (47.26% vs 43.90%), nhưng vẫn chưa đạt ngưỡng. Giả thuyết mới: Thử ETHUSDT thay vì BTC - ETH có thể dẫn dắt altcoin tốt hơn BTC trong phiên Á (do DeFi activity).

### Ý tưởng tiếp theo (Vòng 182 - LeadETH5m_182):
- **Hành động:** Thay BTC bằng ETHUSDT 5min (W20) làm Leading Indicator.
- **Giả thuyết:** ETH có mối tương quan mạnh hơn với LTC (cùng nhóm altcoin), tín hiệu dẫn dắt có thể rõ ràng hơn BTC.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE LeadETH5m_182
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadETH5m_182'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": "run_20260511_210003_v3",
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT",
    "EXECUTION_SYMBOL": "LTCUSDm",
    "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_ASIAN_V6",
    "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.0025, "SL_PCT": 0.002, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]},
            {"SYMBOL": "ETHUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
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
with open('start_train_asian_182.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_182.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tao Run Moi - LEADING INDICATOR (LeadETH5m_182).

📊 Ket qua LeadBTC5m_181:
- Epoch 2. Score: 0.3367. WR: 47.26% (Thr 0.72) | 43.90% (Thr 0.81)
- BTC 5min tot hon BTC 15min (47% vs 44%) nhung van chua dat 60%

🎯 Y tuong moi: Thay BTC bang ETHUSDT 5min
- ETH cung nhom altcoin voi LTC, tuong quan manh hon
- Gia thuyet: ETH dan dat altcoin tot hon BTC trong phien A

🚀 LeadETH5m_182 (PID {pid}) da kich hoat!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py"], check=True)
