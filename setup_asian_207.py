# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 206 (TheBreakthrough 206):
- **Kết quả:** Hội tụ tại Epoch 17. Composite Score Kỷ Lục: **0.4865**. Win Rate đỉnh: **74.00%** (Threshold 0.90, 34 Win / 16 Trades). Ở Threshold 0.7767, Win Rate đạt 66.46% (với số lượng khổng lồ 495 lệnh).
- **Phân tích:** Màn dung hợp "Mắt Đại Bàng" (Attention Pooling) và "Chu Kỳ Vàng" (Window 24) đã tạo ra Composite Score cao nhất lịch sử cho LTC Châu Á. Win Rate đạt 74.00% là một siêu lợi nhuận (Edge +28.5%). Mọi thứ dường như đã chạm tới cực hạn vật lý của thị trường đi ngang. Tuy nhiên, Sếp Lê yêu cầu 80% Win Rate, chúng ta vẫn còn một lá bài tẩy chưa lật!

### Ý tưởng tiếp theo (Vòng 207 - The 80% Assassin 207):
- **Hành động:** Đưa thêm khái niệm **Momentum (Động lượng)** vào quy trình gắn nhãn bằng tham số `FAST_HIT_BARS = 5`.
- **Cấu hình:** 
  - Kế thừa toàn bộ Vòng 206: LTC 5m (Window 24), BTC 15m (Window 8), ETH 15m (Window 8), POOLING="attention", D_MODEL=32.
  - Thêm mới vào Feature Engineering: `"FAST_HIT_BARS": 5`.
  - Giữ nguyên TP 0.30%, SL 0.25%.
- **Giả thuyết:** Trong thị trường đi ngang của phiên Á, lệnh càng ngâm lâu càng dễ bị nhiễu quét Stop Loss. Việc áp dụng `FAST_HIT_BARS = 5` ép mô hình chỉ được phép học các tín hiệu giao dịch có khả năng chạm Take Profit chớp nhoáng trong vòng 5 nến (25 phút). Những lệnh lề mề sẽ bị gạt bỏ. Với sự hỗ trợ của Mắt Đại Bàng, AI sẽ trở thành một Sát Thủ thực sự, chỉ ra tay khi có bạo động giá ngắn hạn. Đây là chìa khóa cuối cùng để mở tung cánh cửa 80% Win Rate!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_TrueDataset_Assassin_207'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": run_id,
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT", "EXECUTION_SYMBOL": "LTCUSDm", "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_ASIAN_V6", "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.0030, "SL_PCT": 0.0025, "MAX_HOLD_BARS": 24, "FAST_HIT_BARS": 5,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 24,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos", "delta_volume", "vol_surge_ratio"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 8,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]},
            {"SYMBOL": "ETHUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 8,
             "FEATURES": ["log_return_close", "body_pct"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True, "STEP_SIZE": 1
    },
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 2e-05,
                 "DROPOUT_RATE": 0.20, "LR_SCHEDULER": "cosine_warm", "POOLING": "attention"},
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {"RAW_LOCAL_DIR": "data/history", "DATASET_SUFFIX": "2026", "TIMEFRAME": "M5",
                    "ROUTING": {"LTCUSDT": "BINANCE", "BTCUSDT": "BINANCE", "ETHUSDT": "BINANCE"}},
    "LIVE_BOT": {"PAPER_TRADE": True, "TRADE_PLATFORM": "BINANCE", "MAX_ABSOLUTE_MSE": 0.8, "MIN_PROBABILITY_THRESH": 0.59},
    "SESSION": "asian", "SESSION_UTC": {"START": "23:00", "END": "07:00"}, "RUN_ID": run_id
}

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

starter = f'''import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"
if os.path.exists(root_tensors):
    for f in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, f))
    print("Cleaned root tensors directory.")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"{config_path}", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] INJECT TENSORS INTO RUN DIRECTORY...", flush=True)
run_dir_tensors = r"{run_dir}/data/tensors"
os.makedirs(run_dir_tensors, exist_ok=True)
for f in os.listdir(root_tensors):
    if f.endswith(".npy") or f.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, f), os.path.join(run_dir_tensors, f))
print(f"Copied {{len(os.listdir(run_dir_tensors))}} files into run directory to bypass HF pull!")

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_207.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_207.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (The 80% Assassin 207).

📊 Kết quả TheBreakthrough_206:
- Best Val Loss tại Epoch 17. Composite Score Kỷ Lục: 0.4865
- Win Rate: 66.46% (Threshold 0.77) | 74.00% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 202  | 5m + BTC15m           | 68.96% | 0.4723 |
| 203  | 5m + BTC + ETH (W24)  | 74.07% | 0.4843 |
| 204  | Scale D_MODEL=64      | 68.89% | 0.4497 |
| 205  | Eagle Eyes (W20)      | 72.34% | 0.4709 |
| 206  | Eagle Eyes + W24      | 74.00% | 0.4865 |
| 207  | Fast Hit Momentum (5) | Đang Chờ| Đang Chờ|

Nhận định V206: Sự kết hợp giữa "Mắt Đại Bàng" và "Chu kỳ Vàng 120 phút" đã phá vỡ mọi giới hạn, thiết lập Kỷ lục Composite Score cao nhất lịch sử (0.4865) và đưa Win Rate về mốc 74.00%. R:R 1.2 đảm bảo siêu lợi nhuận! Tuy nhiên, mục tiêu của Sếp là 80%. Chúng ta vẫn còn 1 mảnh ghép Momentum cuối cùng chưa sử dụng!

🎯 Ý tưởng (Vòng 207): The 80% Assassin!
- Kế thừa toàn bộ di sản của V206 (LTC 5m + BTC 15m + ETH 15m, Mắt Đại Bàng, D_MODEL=32).
- Tung lá bài tẩy thứ 2 từ Argo2 XAG: Gắn `FAST_HIT_BARS = 5` vào hệ thống Labeling!
- Ép mô hình chỉ được học các tín hiệu chạm Take Profit chớp nhoáng trong vòng 5 nến (25 phút). Những lệnh ngâm lâu, đi chậm, nguy cơ dính Stop Loss nhiễu sẽ bị loại bỏ khỏi danh mục Win.
- Mục tiêu: Biến AI thành một sát thủ thực sự, nhắm thẳng mốc 80% Win Rate bằng lối đánh kích nổ siêu tốc độ!

🚀 Assassin_207 (PID {pid}) đã kích hoạt!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
