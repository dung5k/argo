# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. APPEND DIARY - Kết quả V180 + Ý tưởng V181
diary_text = """
### Tóm tắt Vòng 180 (LeadBTC15m_180):
- **Kết quả:** Hội tụ tại Epoch 116. Composite Score: 0.3140. Win Rate đỉnh: **43.90%** (Threshold 0.84).
- **Cấu hình:** LTC 1min (W20) + BTCUSDT 15min (W30) - Lần đầu áp dụng Leading Indicator Strategy.
- **Phân tích:** Thí nghiệm Leading Indicator đầu tiên cho kết quả chưa tốt. BTC 15min có thể quá chậm (khung lớn) so với LTC 1min, tạo ra độ trễ pha quá lớn khiến bộ não khó học được quy luật dẫn dắt. Cần thử BTC trên khung nhỏ hơn (5min) để giảm độ trễ.

### Ý tưởng tiếp theo (Vòng 181 - LeadBTC5m_181):
- **Hành động:** Thử BTCUSDT 5min (W20) thay vì 15min (W30) để giảm độ trễ pha.
- **Giả thuyết:** BTC 5min sẽ cho tín hiệu dẫn dắt nhanh hơn, đồng bộ hơn với LTC 1min.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE LeadBTC5m_181
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC5m_181'
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
    "HF_CLOUD": {
        "DATASET_REPO": "dung5k/argo_workspaces",
        "MODEL_REPO": "dung5k/argo_workspaces",
        "SYNC_CHUNKS": True
    },
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.0025,
        "SL_PCT": 0.002,
        "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct",
        "PIP_SIZE": 0.01,
        "lot_size": 0.1,
        "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {
                "SYMBOL": "LTCUSDT",
                "TIMEFRAME": "1min",
                "WINDOW_SIZE": 20,
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
                "WINDOW_SIZE": 20,
                "FEATURES": [
                    "log_return_close",
                    "body_pct",
                    "bb_width",
                    "rsi_14_scaled"
                ]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True
    },
    "TRAINING": {
        "D_MODEL": 32,
        "N_HEAD": 4,
        "NUM_LAYERS": 2,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 60,
        "LEARNING_RATE": 2e-05,
        "DROPOUT_RATE": 0.25,
        "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {
        "BINANCE": "LOCAL"
    },
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "data/history",
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
    "SESSION": "asian",
    "SESSION_UTC": {
        "START": "23:00",
        "END": "07:00"
    },
    "RUN_ID": run_id
}

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

# 3. Launch training
starter = f'''import subprocess, os, sys
run_id = "{run_id}"
config_path = r"{config_path}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Leading Indicator: LTC 1min + BTC 5min (giam do tre)...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
'''
with open('start_train_asian_181.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_181.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# 4. TELEGRAM
msg = f"""🏯 [ASIAN V6 MTF] Tao Run Moi - LEADING INDICATOR (LeadBTC5m_181).

📊 Ket qua LeadBTC15m_180:
- Best Val Loss tai Epoch 116. Composite Score: 0.3140
- Win Rate: 43.37% (Threshold 0.74) | 43.90% (Threshold 0.84)
- Nhan dinh: BTC 15min qua cham, do tre pha qua lon so voi LTC 1min

🎯 Y tuong moi LeadBTC5m_181:
- Input 1: LTCUSDT 1min (W20) - Tin hieu goc
- Input 2: BTCUSDT 5min (W20) - BTC khung nho hon de giam do tre
- TP: 0.25% | SL: 0.20% | D_MODEL: 32

🚀 LeadBTC5m_181 (PID {pid}) da kich hoat! Muc tieu: Pha ky luc 77.27% bang Leading Indicator voi do tre thap hon!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)

sp.run(["python", "scratch/send_tele_wrapper.py"], check=True)
