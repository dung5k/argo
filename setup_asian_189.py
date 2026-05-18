# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 188 (LeadBTC1m_GiantBrain_188):
- **Kết quả:** Hội tụ tại Epoch 166 (Early Stopping). Composite Score: 0.3008. Win Rate đỉnh: **45.45%** (Threshold 0.86).
- **Cấu hình:** LTC 1min + BTC 1min + Giant Brain (D_MODEL=128, N_HEAD=8, NUM_LAYERS=4).
- **Phân tích:** Việc tăng kích thước mạng lên quá lớn đã gây ra thảm họa (Win Rate tụt thẳng xuống 45.45%). Ma trận dữ liệu tick-by-tick (1m) chứa quá nhiều nhiễu ngẫu nhiên, khi đi qua mạng lưới nơ-ron khổng lồ đã dẫn đến hiện tượng Overfitting trầm trọng (học thuộc lòng nhiễu thay vì quy luật cốt lõi). Bức tường 56% không phải do thiếu Capacity mà là do Tỷ lệ Nhiễu/Tín hiệu (Noise-to-Signal) quá cao.

### Ý tưởng tiếp theo (Vòng 189 - LeadBTC_MicroWindow_189):
- **Hành động:** Quay lại cấu trúc mạng nhỏ (Golden Config: D_MODEL=32, LR=2e-5) để ngăn Overfitting. Thay đổi chiến thuật độ dài cửa sổ (Window Size) cho BTC: Thay vì bắt BTC phải nhìn 20 nến (giống LTC), ta chỉ cho BTC nhìn **5 nến gần nhất (W=5)**.
- **Giả thuyết:** Leading Indicator trong Micro-Scalping chỉ nên cung cấp "Cú hích tức thời" (Immediate Trigger). Nếu BTC đột ngột có biến động lớn hoặc dòng tiền đột biến trong 5 phút vừa qua, đó mới là tín hiệu dẫn dắt đáng tin cậy. Việc đưa 20 nến BTC vào mạng nơ-ron chỉ làm tăng thêm nhiễu lịch sử không cần thiết.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC1m_MicroWindow_189'
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
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 5,
             "FEATURES": ["log_return_close", "delta_volume"]}
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
with open('start_train_asian_189.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_189.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC_MicroWindow_189).

📊 Kết quả V188 (Giant Brain D128):
- Best Val Loss tại Epoch 30. Composite Score: 0.3008
- Win Rate: 45.45% (Threshold 0.86) | 34.15% (Threshold 0.75)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 183  | LTC 1m + BTC 5m (D64) | 54.72% | 0.3584 |
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |
| 188  | Giant Brain (D128)    | 45.45% | 0.3008 |

Nhận định: Giant Brain (V188) là một bước lùi thảm hại. Mạng lưới khổng lồ không thể xử lý dữ liệu vi mô (1 phút) của 2 mã kết hợp mà chỉ bị Overfitting. Tỷ lệ Nhiễu/Tín hiệu (Noise-to-Signal) đang ở mức rất cao.

🎯 Ý tưởng mới (Vòng 189): Chiến thuật Micro-Window!
- Trở lại kích thước mạng "Vàng" (D_MODEL=32) để kháng nhiễu.
- LTCUSDT 1min tiếp tục dùng Window=20 (bắt sóng 20 phút).
- ĐỘT PHÁ: BTCUSDT 1min giảm mạnh Window xuống còn 5 (chỉ nhìn 5 phút gần nhất).
- Giả thuyết: Trong Micro-Scalping, chỉ báo dẫn dắt chỉ nên là một "Cú Hích Tức Thời". Khối lượng và giá BTC bùng nổ trong 5 phút vừa qua sẽ kích hoạt dòng tiền vào LTC, còn xa hơn 5 phút chỉ là nhiễu vô ích.

🚀 LeadBTC_MicroWindow_189 (PID {pid}) đã kích hoạt! Mục tiêu: Vượt bức tường 56%!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
