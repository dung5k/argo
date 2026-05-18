# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 186 (LeadBTC_OrderFlow_186):
- **Kết quả:** Hội tụ tại Epoch 4. Composite Score: 0.3512. Win Rate đỉnh: **56.25%** (Threshold 0.92).
- **Cấu hình:** LTC 1min + BTC 1min (tập trung OrderFlow: delta_volume, vol_surge_ratio) + D_MODEL=64.
- **Phân tích:** Kết quả y hệt Vòng 184 (cũng 56.25%). Điều này chứng tỏ việc thay đổi Feature từ Price Action sang OrderFlow cho BTC không mang lại giá trị gia tăng nào đáng kể. Có vẻ BTC tuy là anh cả thị trường nhưng có độ trễ/nhiễu so với LTC ở khung siêu ngắn (1 phút).

### Ý tưởng tiếp theo (Vòng 187 - LeadETH1m_D64_187):
- **Hành động:** Thay thế BTC bằng **ETHUSDT 1min**. Giữ nguyên Base 1min cho LTC.
- **Giả thuyết:** ETH có vốn hóa nhỏ hơn BTC và biến động có thể "sát" với các Altcoin như LTC hơn. Sự tương quan giữa ETH và LTC trong hệ sinh thái Altcoin có thể mượt mà hơn và ít bị nhiễu bởi các thuật toán Market Maker khổng lồ của BTC. Ta sẽ thử xem ETH có phải là một Leading Indicator tốt hơn BTC ở khung 1 phút hay không.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadETH1m_D64_187'
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
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]},
            {"SYMBOL": "ETHUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
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
with open('start_train_asian_187.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_187.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadETH1m_D64_187).

📊 Kết quả V186 (LTC 1m + BTC 1m OrderFlow):
- Best Val Loss tại Epoch 4. Composite Score: 0.3512
- Win Rate: 56.25% (Threshold 0.92) | 49.76% (Threshold 0.79)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 181  | LTC 1m + BTC 5m (D32) | 47.26% | 0.3367 |
| 182  | LTC 1m + ETH 5m (D32) | 45.33% | 0.3427 |
| 183  | LTC 1m + BTC 5m (D64) | 54.72% | 0.3584 |
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |

Nhận định: BTC (cả Price Action lẫn OrderFlow) đều dường như tạo ra một "Bức Tường 56%" không thể vượt qua đối với LTC ở khung 1 phút. Có lẽ tương quan BTC-LTC ở tầm vi mô là quá nhiễu.

🎯 Ý tưởng mới (Vòng 187): Thay thế BTC bằng ETH!
- Sử dụng ETHUSDT 1min (W20) làm Leading Indicator cho LTC 1min.
- Giữ cấu hình Vàng: D_MODEL=64, LR=2e-5.
- Giả thuyết: ETH (Vua của Altcoin) có thể có hệ số tương quan tuyến tính ngắn hạn với LTC tốt hơn so với BTC, từ đó cung cấp tín hiệu dẫn dắt mượt mà hơn.

🚀 LeadETH1m_D64_187 (PID {pid}) đã kích hoạt! Mục tiêu: Phá vỡ bức tường 56%!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
