# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ========== LEADING INDICATOR STRATEGY - VÒNG 180 ==========
# Ý tưởng: Lấy cấu hình TOP 1 (1min W20, WR 77.27%) làm nền tảng
# Bổ sung BTCUSDT 15min làm chỉ báo dẫn dắt (Leading Indicator)
# Giả thuyết: BTC biến động trước LTC, khung 15min cho tầm nhìn xa

# 1. APPEND TO DIARY
diary_text = """
### === GIAI ĐOẠN MỚI: LEADING INDICATOR STRATEGY ===
### Tóm tắt Vòng 180 (LeadBTC_180):
- **Ý tưởng:** Áp dụng Định Hướng Chiến Lược mới của Sếp Lê - Chỉ Báo Dẫn Dắt.
- **Cấu hình:** Lấy nền tảng TOP 1 (1min W20, TP=0.0025/SL=0.002) + Bổ sung BTCUSDT 15min (W30) làm Leading Indicator.
- **Giả thuyết:** BTC là đồng tiền dẫn dắt toàn thị trường crypto. Khi BTC biến động trên khung 15 phút, LTC thường phản ứng theo sau. Bộ não sẽ học quy luật trễ pha (Phase Lag) giữa BTC và LTC.
- **Kiến trúc:** D_MODEL=32, N_HEAD=4, NUM_LAYERS=2 (giữ nhẹ như TOP 1).
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE LeadBTC_180
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC15m_180'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

# Build config with Leading Indicator
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
        "⚠️_STRICT_WARNING_⚠️": "TẤT CẢ MODULE MACRO_FEATURES LÀ BẮT BUỘC.",
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
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 30,
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
print("Leading Indicator Strategy: LTC 1min + BTC 15min...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
'''
with open('start_train_asian_180.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_180.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# 4. TELEGRAM
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới - LEADING INDICATOR (LeadBTC_180).

🎯 CHIẾN LƯỢC MỚI: CHỈ BÁO DẪN DẮT
Lần đầu tiên áp dụng định hướng của Sếp Lê: Tìm mã biến động TRƯỚC LTC.

📐 Cấu hình LeadBTC_180:
- Input 1: LTCUSDT 1min (W20) - Tín hiệu gốc
- Input 2: BTCUSDT 15min (W30) - CHỈ BÁO DẪN DẮT MỚI
- TP: 0.25% | SL: 0.20% (Micro-Scalping)
- D_MODEL: 32 | LR: 2e-5

Giả thuyết: BTC biến động trước LTC. Khung 15 phút BTC cho tầm nhìn xa, bộ não sẽ học quy luật trễ pha giữa BTC và LTC.

🚀 LeadBTC_180 (PID {pid}) đã kích hoạt! Mục tiêu: Phá vỡ kỷ lục 77.27% bằng sức mạnh của Leading Indicator!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)

sp.run(["python", "scratch/send_tele_wrapper.py"], check=True)
