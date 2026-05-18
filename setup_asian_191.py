# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 190 (LeadBTC_PurePrice_190):
- **Kết quả:** Hội tụ tại Epoch 16. Composite Score: 0.3532. Win Rate đỉnh: **51.43%** (Threshold 0.88).
- **Cấu hình:** LTC 1m + BTC 1m (Chỉ dùng duy nhất Feature `log_return_close`) + D_MODEL=32.
- **Phân tích:** Việc loại bỏ toàn bộ OrderFlow và các indicator khác làm Win Rate cắm đầu xuống 51.43%. Điều này chứng minh rằng các Feature kỹ thuật (RSI, Bollinger) và OrderFlow không phải là nguyên nhân gây nhiễu, mà bản thân việc kết hợp 2 symbol ở khung siêu ngắn (1 phút) là bất khả thi vì tiếng ồn thị trường quá lớn (Market Noise).

### Ý tưởng tiếp theo (Vòng 191 - Base15m_Lead15m_191):
- **Hành động:** Sử dụng đặc quyền linh hoạt Timeframe được Sếp cấp. Từ bỏ hoàn toàn khung 1 phút cho chiến lược Leading Indicator. Nâng Base Timeframe của LTC và BTC lên **15 phút**. Tăng TP lên 0.60% và SL 0.40% cho phù hợp sóng 15m. Khôi phục lại toàn bộ Features (OrderFlow, Price Action) và D_MODEL=64.
- **Giả thuyết:** Khung 1 phút (Micro-Scalping) có tỷ lệ nhiễu cực cao khiến AI không thể tìm ra sự dẫn dắt tuyến tính giữa BTC và LTC. Bằng cách nâng lên khung 15 phút, các tín hiệu nhiễu vi mô sẽ bị triệt tiêu, để lộ ra bức tranh Dòng tiền Vĩ mô (Macro Trend). Ở khung này, một sự dịch chuyển của BTC (Leading) mới thực sự mang tính định hướng cho LTC.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_15m_Lead15m_D64_191'
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
        "TP_PCT": 0.0060, "SL_PCT": 0.0040, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "delta_volume", "hour_sin", "hour_cos"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "delta_volume", "vol_surge_ratio"]}
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
with open('start_train_asian_191.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_191.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (Base15m_Lead15m_191).

📊 Kết quả V190 (LTC 1m + BTC 1m Pure Price Action):
- Best Val Loss tại Epoch 16. Composite Score: 0.3532
- Win Rate: 51.43% (Threshold 0.88) | 39.64% (Threshold 0.76)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |
| 188  | Giant Brain (D128)    | 45.45% | 0.3008 |
| 189  | Micro Window (BTC W5) | 50.00% | 0.3491 |
| 190  | Pure Price (No Flow)  | 51.43% | 0.3532 |

Nhận định: Việc cắt bỏ Features để giảm nhiễu (V190) thất bại. Vấn đề không nằm ở thuật toán (Giant Brain) hay độ trễ (Window) hay nhiễu tính năng (Pure Price), mà nằm ở bản chất dữ liệu 1 phút kết hợp quá nhiễu, thị trường chưa kịp đồng pha.

🎯 Ý tưởng mới (Vòng 191): Khung Vĩ Mô 15 Phút!
- Kích hoạt đặc quyền thay đổi Base Timeframe: Nâng LTC và BTC lên khung 15 phút.
- Khôi phục vũ khí hạng nặng: Order Flow + Đầy đủ Price Action.
- Tăng TP lên 0.6% và SL 0.4% (phù hợp sóng 15m).
- Giả thuyết: Khung 15m sẽ triệt tiêu biến động ngẫu nhiên. Ở góc nhìn vĩ mô này, "Cú hích" của BTC mới thực sự dẫn dắt LTC một cách đồng bộ và rõ ràng.

🚀 Base15m_Lead15m_191 (PID {pid}) đã kích hoạt! Mục tiêu: Rời bỏ đáy 56% để bay cao!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
