# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 192 (LeadBTC_ContextOnly_192):
- **Kết quả:** Hội tụ tại Epoch 40. Composite Score: 0.3257. Win Rate đỉnh: **45.83%** (Threshold 0.90).
- **Cấu hình:** LTC 1m (W20) + BTC 15m (W1 - Context Only) + D_MODEL=64.
- **Phân tích:** Ngay cả khi giảm thiểu nhiễu bằng cách chỉ lấy đúng 1 nến vĩ mô (W=1) của BTC làm màng lọc ngữ cảnh, hệ thống vẫn thất bại thảm hại (45.83%). Trải qua 13 vòng thử nghiệm liên tục với mọi biến thể (BTC, ETH, 1m, 5m, 15m, Price Action, Order Flow, Giant Brain, Micro-Window, Context Only), **Win Rate chưa bao giờ vượt qua 56.52%**.

### Ý tưởng tiếp theo (Vòng 193 - SingleSymbol_HolyGrail_193):
- **Hành động:** Thực thi ĐẶC QUYỀN "Toàn quyền quyết định thêm/bớt SYMBOL": **BỚT (LOẠI BỎ) HOÀN TOÀN CHỈ BÁO DẪN DẮT**. Quay về cấu trúc Single-Symbol (Chỉ dùng LTCUSDT 1 phút). Tăng cường sức mạnh bằng cách dồn toàn bộ tinh hoa Feature (Price Action + Order Flow: `delta_volume`, `vol_surge_ratio`) vào duy nhất mảng LTC.
- **Giả thuyết:** Khẳng định: **Chiến lược Leading Indicator bị "phá sản" hoàn toàn trong phiên Á (Micro-Scalping)**. Phiên Á thanh khoản mỏng, các mã di chuyển tách biệt và bị chi phối bởi Market Maker nội bộ từng mã ở khung 1 phút chứ không tuân theo dòng tiền lan tỏa (Ripple Effect) từ BTC như phiên London/NY. Việc đưa thêm BTC/ETH chỉ làm AI bị nhiễu do "Correlation Illusion" (Ảo giác tương quan). Bằng cách dồn toàn lực vào một mã duy nhất (LTC), ta kỳ vọng tái lập lại hoặc vượt mốc kỷ lục cũ 77.27%.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_SingleSymbol_HolyGrail_193'
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
        "TP_PCT": 0.0035, "SL_PCT": 0.0015, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "delta_volume", "vol_surge_ratio", "hour_sin", "hour_cos"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 1.5e-05,
                 "DROPOUT_RATE": 0.20, "LR_SCHEDULER": "cosine_warm"},
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
with open('start_train_asian_193.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_193.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (SingleSymbol_HolyGrail_193).

📊 Kết quả V192 (Context Only BTC 15m W1):
- Best Val Loss tại Epoch 40. Composite Score: 0.3257
- Win Rate: 45.83% (Threshold 0.90) | 43.05% (Threshold 0.77)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |
| 188  | Giant Brain (D128)    | 45.45% | 0.3008 |
| 189  | Micro Window (BTC W5) | 50.00% | 0.3491 |
| 190  | Pure Price (No Flow)  | 51.43% | 0.3532 |
| 191  | Base 15m + Lead 15m   | 47.06% | 0.3421 |
| 192  | Context Only (BTC 15m)| 45.83% | 0.3257 |

Nhận định: Mọi nỗ lực ép AI dùng Leading Indicator (13 vòng, đủ mọi biến thể) đều thất bại trong việc vượt mốc 56.52%. Điều này minh chứng: Tại phiên Á (Scalping 1m), dòng tiền độc lập. Việc ghép mã dẫn dắt chỉ tạo ra "Ảo giác tương quan" (Correlation Illusion) khiến AI bị nhiễu.

🎯 Ý tưởng mới (Vòng 193): Khẳng định Holy Grail là Single Symbol!
- Thực thi quyền "Toàn Quyền Bớt Symbol": LOẠI BỎ hoàn toàn BTC/ETH. Trở về cấu trúc Single Input (Chỉ có LTCUSDT 1m W20).
- Dồn toàn bộ hỏa lực vào LTC: Tích hợp đầy đủ Price Action + Order Flow (`delta_volume`, `vol_surge_ratio`).
- Thiết lập TP 0.35%, SL 0.15% (R:R > 1.2).
- Giả thuyết: Phiên Á cần sự tĩnh lặng để phân tích dòng tiền vi mô nội bộ của chính đồng coin đó. Loại bỏ nhiễu từ các đồng khác sẽ giúp mạng nơ-ron đánh hơi được dòng chảy thực sự của LTC.

🚀 SingleSymbol_HolyGrail_193 (PID {pid}) đã kích hoạt! Mục tiêu: Tái lập kỷ lục 77%!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
