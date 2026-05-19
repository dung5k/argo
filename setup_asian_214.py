import codecs
import time
import os
import json
import subprocess as sp

# 1. DIARY
diary_text = """# NHẬT KÝ ĐÀO TẠO V6 ASIAN

### Tóm tắt Vòng 213 (The Deep Micro-Architect 213):
- **Kết quả:** Hội tụ tại Epoch 80. Composite Score: **0.0817**. Win Rate: **89.19%** (Threshold 0.82, 37 lệnh).
- **Phân tích:** Cải thiện nhẹ so với V212 (Score tăng từ 0.0746 lên 0.0817) nhờ trả Dropout về 0.15 và chuyển sang mạng sâu hẹp (D=32, L=4). Tuy nhiên, kết quả vẫn kém xa mốc V210 (Score 0.1069, WR 96.97%). Điều này chứng tỏ việc làm mạng quá sâu hoặc áp dụng Dropout quá lớn đang bóp nghẹt luồng thông tin học tập của phiên Á vốn dĩ có thanh khoản mỏng và biên độ giá cực kỳ hẹp.

### Ý tưởng tiếp theo (Vòng 214 - The Balanced Capacity Scaler):
- **Hành động:** Tiếp tục đơn giản hóa mô hình về cấu trúc tối ưu của V210 nhưng tinh chỉnh lại các tham số regularizer để giải phóng dung lượng biểu diễn (representation capacity).
- **Cấu hình:**
  - Giữ `D_MODEL` = 32.
  - Giảm `NUM_LAYERS` về 3 (giống V210) để tránh hiện tượng tiêu biến gradient và quá tải độ sâu.
  - Giảm `DROPOUT_RATE` xuống **0.08** (thay vì 0.15) để cho phép các neuron giữ lại nhiều thông tin đặc trưng của OrderFlow hơn.
  - `N_HEAD` = 8 (giúp đa dạng hóa góc nhìn Attention).
  - Giữ nguyên Base TF 5m, Window 24, Fast Hit 5, Attention Pooling, LR=1e-5.
- **Giả thuyết:** Bằng cách giảm thiểu Dropout xuống 0.08 và giữ độ sâu ở mức 3 tầng, mô hình sẽ đạt được trạng thái cân bằng dung lượng hoàn hảo cho phiên Á, giúp khôi phục Score vượt mốc 0.11 và ổn định tỷ lệ thắng cực cao.
"""

diary_file = 'workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md'
os.makedirs(os.path.dirname(diary_file), exist_ok=True)

if os.path.exists(diary_file):
    with codecs.open(diary_file, 'a', encoding='utf-8') as f:
        f.write("\n" + diary_text)
else:
    with codecs.open(diary_file, 'w', encoding='utf-8') as f:
        f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_BalancedCapacity_214'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": run_id,
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
        "TP_PCT": 0.0030,
        "SL_PCT": 0.0025,
        "MAX_HOLD_BARS": 24,
        "FAST_HIT_BARS": 5,
        "LABEL_MODE": "pct",
        "PIP_SIZE": 0.01,
        "lot_size": 0.1,
        "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {
                "SYMBOL": "LTCUSDT",
                "TIMEFRAME": "5min",
                "WINDOW_SIZE": 24,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos", "delta_volume", "vol_surge_ratio"]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 8,
                "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]
            },
            {
                "SYMBOL": "ETHUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 8,
                "FEATURES": ["log_return_close", "body_pct"]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True,
        "STEP_SIZE": 1
    },
    "TRAINING": {
        "D_MODEL": 32,
        "N_HEAD": 8,
        "NUM_LAYERS": 3,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 80,
        "LEARNING_RATE": 1e-05,
        "DROPOUT_RATE": 0.08,
        "LR_SCHEDULER": "cosine_warm",
        "POOLING": "attention"
    },
    "MT5_PATHS": {
        "BINANCE": "LOCAL"
    },
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "data/history",
        "DATASET_SUFFIX": "2026",
        "TIMEFRAME": "M5",
        "ROUTING": {
            "LTCUSDT": "BINANCE",
            "BTCUSDT": "BINANCE",
            "ETHUSDT": "BINANCE"
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

starter = f'''import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"
if os.path.exists(root_tensors):
    for f in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, f))
    print("Cleaned root tensors directory.")

print(">>> [PHASE 0.1] PREPARE RAW DATA PARQUETS...", flush=True)
raw_dir = "workspaces/CFG_LTC_ASIAN_V6/data/raw"
os.makedirs(raw_dir, exist_ok=True)
for sym_file in ["LTCUSDT_BINANCE_1M_2026.parquet", "BTCUSDT_BINANCE_1M_2026.parquet", "ETHUSDT_BINANCE_1M_2026.parquet"]:
    src = os.path.join("data/history", sym_file)
    dst = os.path.join(raw_dir, sym_file)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"Copied {sym_file} to raw directory.")

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

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''

with open('start_train_asian_214.py', 'w', encoding='utf-8') as f:
    f.write(starter)

print(f"SUCCESS: Created run folder and generated setup config for {run_id}")
