# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 185 (LeadBTC5m_Base5m_185):
- **Kết quả:** Hội tụ tại Epoch 4. Composite Score: 0.3681. Win Rate đỉnh: **56.52%** (Threshold 0.92).
- **Cấu hình:** LTC 5min (W20) + BTC 5min (W20) + D_MODEL=64 + TP/SL (0.35%/0.2%).
- **Phân tích:** Việc nâng Base Timeframe lên 5 phút hầu như không cải thiện Win Rate (56.52% so với 56.25% của khung 1 phút). Có vẻ như vấn đề không nằm ở Timeframe mà nằm ở bộ Features của chỉ báo dẫn dắt (chỉ dùng giá/OHLC). 

### Ý tưởng tiếp theo (Vòng 186 - LeadBTC1m_OrderFlow_186):
- **Hành động:** Quay lại Base 1 phút (vì khung này cho ra baseline 77.27%). Thay đổi toàn diện Feature Engineering của Leading Indicator: Áp dụng OrderFlow (`delta_volume`, `vol_surge_ratio`) cho cả BTC 1min và LTC 1min.
- **Giả thuyết:** Thay vì chỉ quan tâm đến biến động giá (điều có thể bị lag hoặc ngẫu nhiên), hệ thống sẽ theo dõi Dòng Tiền (OrderFlow) của BTC. Sự bùng nổ khối lượng mua/bán ở BTC (dòng tiền lớn) sẽ là tín hiệu dẫn dắt đáng tin cậy hơn cho sự di chuyển của LTC sau đó.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC_OrderFlow_D64_186'
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
        "TP_PCT": 0.0025, "SL_PCT": 0.002, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "delta_volume", "hour_sin", "hour_cos"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "delta_volume", "vol_surge_ratio"]}
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
with open('start_train_asian_186.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_186.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC_OrderFlow_186).

📊 Kết quả V185 (LTC 5m + BTC 5m + D_MODEL 64):
- Best Val Loss tại Epoch 4. Composite Score: 0.3681
- Win Rate: 56.52% (Threshold 0.92) | 48.00% (Threshold 0.79)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 180  | LTC 1m + BTC 15m (D32)| 43.90% | 0.3140 |
| 181  | LTC 1m + BTC 5m (D32) | 47.26% | 0.3367 |
| 182  | LTC 1m + ETH 5m (D32) | 45.33% | 0.3427 |
| 183  | LTC 1m + BTC 5m (D64) | 54.72% | 0.3584 |
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |

Nhận định: Việc chuyển sang khung 5 phút không tạo ra đột phá (chỉ tăng 0.27%). Dữ liệu giá thuần túy (Price Action) của BTC dường như tạo ra quá nhiều nhiễu.

🎯 Ý tưởng mới (Vòng 186): Tập trung vào OrderFlow của BTC!
- Quay lại Base Timeframe 1 phút (môi trường lý tưởng của kỷ lục 77%).
- Bổ sung các features Dòng Tiền (OrderFlow): `delta_volume`, `vol_surge_ratio` cho BTC 1min thay vì các chỉ báo giá thông thường.
- Giả thuyết: Dòng tiền lớn chảy vào/ra khỏi BTC sẽ dẫn dắt thị trường chính xác hơn là chỉ nhìn vào hành vi giá (thường bị quét râu).

🚀 LeadBTC_OrderFlow_186 (PID {pid}) đã kích hoạt! Mục tiêu: Bắn thủng mốc 60% WR!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
