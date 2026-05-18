# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 191 (Base15m_Lead15m_191):
- **Kết quả:** Hội tụ tại Epoch 77 (Early Stopping). Composite Score: 0.3421. Win Rate đỉnh: **47.06%** (Threshold 0.87).
- **Cấu hình:** LTC 15m + BTC 15m + D_MODEL=64.
- **Phân tích:** Việc chuyển dịch sang khung Vĩ Mô (15 phút) đã thất bại thảm hại, WR rớt xuống 47.06%. Điều này khẳng định phiên Châu Á không có sóng macro (xu hướng dài hạn) đáng kể. Lợi nhuận của phiên Á hoàn toàn nằm ở việc bắt các sóng ngắn (Micro-Scalping 1 phút).

### Ý tưởng tiếp theo (Vòng 192 - LeadBTC_ContextOnly_192):
- **Hành động:** Quay lại Base 1 phút cho LTC (W=20). Giữ BTC làm Leading Indicator nhưng áp dụng chiến thuật **"Context Only" (Chỉ lấy Bối cảnh)**: Sử dụng khung 15 phút cho BTC nhưng **WINDOW_SIZE = 1**.
- **Giả thuyết:** Trong 11 vòng thất bại vừa qua, chúng ta đã đưa quá nhiều dữ liệu lịch sử của chỉ báo dẫn dắt vào mạng lưới (W=20 hoặc W=5), tạo ra nhiễu. Bằng cách ép BTC dùng khung 15m với W=1, hệ thống sẽ chỉ nhận được đúng 1 vector dữ liệu mô tả "Trạng thái Vĩ mô hiện tại" (Current Macro Context) của BTC (ví dụ: Cây nến 15m hiện tại của BTC đang xanh hay đỏ, volume lớn hay nhỏ). AI sẽ dùng duy nhất ngữ cảnh này làm "màng lọc" cho tín hiệu Micro-Scalping của LTC. Đây là cách kết hợp hoàn hảo giữa Leading Indicator và Micro-Scalping mà không gây bùng nổ số chiều nhiễu.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC15m_ContextOnly_192'
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
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 1,
             "FEATURES": ["log_return_close", "body_pct", "vol_surge_ratio"]}
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
with open('start_train_asian_192.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_192.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC_ContextOnly_192).

📊 Kết quả V191 (Khung Vĩ Mô 15m):
- Best Val Loss tại Epoch 77. Composite Score: 0.3421
- Win Rate: 47.06% (Threshold 0.87) | 45.83% (Threshold 0.75)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |
| 188  | Giant Brain (D128)    | 45.45% | 0.3008 |
| 189  | Micro Window (BTC W5) | 50.00% | 0.3491 |
| 190  | Pure Price (No Flow)  | 51.43% | 0.3532 |
| 191  | Base 15m + Lead 15m   | 47.06% | 0.3421 |

Nhận định: Chuyển toàn bộ hệ thống sang khung 15 phút (V191) là một thất bại. Phiên Châu Á bản chất là đi ngang biên độ hẹp, không có sóng dài hạn, nên phải dùng khung 1 phút (Micro-Scalping).

🎯 Ý tưởng mới (Vòng 192): Kỹ thuật "Context Only" (Chỉ Lấy Bối Cảnh)!
- Khôi phục vũ khí mạnh nhất: LTCUSDT 1 phút (Window=20).
- BTCUSDT làm Leading Indicator nhưng dùng khung 15 phút với **WINDOW_SIZE = 1**.
- Giả thuyết: Đưa một ma trận BTC dài ngoằng vào mô hình sẽ gây ngợp. Bằng cách set Window=1 cho khung 15 phút, ta chỉ cấp cho não bộ AI đúng 1 vector thông tin duy nhất: "Trong 15 phút hiện tại, vĩ mô BTC đang tăng hay giảm?". Cực kỳ sạch, không nhiễu, giúp AI dùng nó làm màng lọc định hướng cho các lệnh scalp 1 phút của LTC.

🚀 LeadBTC_ContextOnly_192 (PID {pid}) đã kích hoạt! Mục tiêu: Khoan thủng bức tường 56%!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
