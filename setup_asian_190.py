# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 189 (LeadBTC_MicroWindow_189):
- **Kết quả:** Hội tụ tại Epoch 6. Composite Score: 0.3491. Win Rate đỉnh: **50.00%** (Threshold 0.86).
- **Cấu hình:** LTC 1m (W20) + BTC 1m (W5) + D_MODEL=32.
- **Phân tích:** Việc thu hẹp Window của BTC xuống còn 5 nến không những không giúp ích mà còn làm Win Rate giảm mạnh xuống 50% (thấp hơn nhiều so với 56% của W20). Điều này cho thấy mô hình bị mất đi bối cảnh (context) cần thiết từ BTC để ra quyết định, nhưng nếu đưa đủ bối cảnh thì lại vướng "Bức tường 56%".

### Ý tưởng tiếp theo (Vòng 190 - LeadBTC_PurePrice_190):
- **Hành động:** Quay lại Window=20 cho cả hai. Đột phá ở khâu Feature Engineering: **Cắt bỏ toàn bộ các indicator nhiễu**. Chỉ sử dụng duy nhất một feature cơ bản nhất là `log_return_close` cho cả LTC và BTC.
- **Giả thuyết:** Hệ thống có thể đã bị "ngộ độc" dữ liệu do có quá nhiều features kết hợp (RSI, Bollinger Bands, Order Flow) tạo ra một Feature Space quá phức tạp trên khung 1 phút. Bằng cách gọt sạch mọi thứ và chỉ giữ lại Pure Price Action (Biến động giá thuần túy), AI sẽ buộc phải tập trung tìm kiếm quy luật tương quan giá trực tiếp giữa BTC và LTC mà không bị đánh lạc hướng.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC1m_PurePrice_190'
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
             "FEATURES": ["log_return_close"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close"]}
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
with open('start_train_asian_190.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_190.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC_PurePrice_190).

📊 Kết quả V189 (LTC W20 + BTC W5):
- Best Val Loss tại Epoch 6. Composite Score: 0.3491
- Win Rate: 50.00% (Threshold 0.86) | 43.58% (Threshold 0.75)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |
| 188  | Giant Brain (D128)    | 45.45% | 0.3008 |
| 189  | Micro Window (BTC W5) | 50.00% | 0.3491 |

Nhận định: Việc thu hẹp Window của BTC làm giảm WR xuống tận 50%, chứng tỏ AI vẫn cần bối cảnh lịch sử của chỉ báo dẫn dắt. Tuy nhiên, nếu cung cấp đủ bối cảnh (W20) thì lại bị vướng bức tường 56%.

🎯 Ý tưởng mới (Vòng 190): "Gọt" sạch mọi thứ - Pure Price Action!
- Giữ nguyên cấu trúc Mạng Vàng D_MODEL=32 và Window=20 cho cả LTC/BTC.
- CẮT BỎ TOÀN BỘ indicator (RSI, Bollinger Bands, Volume, v.v.).
- Chỉ giữ lại duy nhất 1 Feature: `log_return_close` cho cả 2 mã.
- Giả thuyết: Mô hình đang bị "ngộ độc dữ liệu" do kết hợp quá nhiều feature rườm rà trên khung 1 phút (rất nhiễu). Bằng cách ép AI chỉ nhìn vào Biến động Giá Thuần Túy, nó sẽ buộc phải tập trung tìm ra độ trễ pha (Lag) giữa BTC và LTC mà không bị phân tâm.

🚀 LeadBTC_PurePrice_190 (PID {pid}) đã kích hoạt! Mục tiêu: Tối giản để đột phá!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
