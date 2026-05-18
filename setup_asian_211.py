import codecs, time, os, json, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 210 (The Clean Slate 210):
- **Kết quả:** Đỉnh tại Epoch 355. Composite Score: **0.1069**. Win Rate đạt **78.86%** (Threshold 0.74, 123 lệnh) và **96.96%** (Threshold 0.85, 33 lệnh).
- **Phân tích:** Mặc dù bị bộ đếm Fast Trade Simulator ép chặt, V210 (huấn luyện từ Scratch) đã chứng minh sức mạnh của cấu hình Attention + W24 + FastHit 5. Mốc 80% Win Rate ở mức tín hiệu dồi dào (Threshold 0.74) chỉ còn cách 1.14%.

### Ý tưởng tiếp theo (Vòng 211 - The Capacity Scaling):
- **Hành động:** Nâng cấp dung lượng nơ-ron (Capacity) để AI có khả năng học các pattern phức tạp hơn.
- **Cấu hình:**
  - Tăng `D_MODEL` từ 32 lên 64.
  - Tăng `NUM_LAYERS` từ 2 lên 3.
  - Tăng `N_HEAD` từ 4 lên 8.
  - Điều chỉnh `DROPOUT_RATE` nhẹ lên 0.20 để bù đắp cho việc tăng Capacity.
  - Giữ nguyên các thông số tinh hoa khác: Base TF 5m, Window 24, Fast Hit 5, Attention Pooling, LR=1e-5.
- **Giả thuyết:** Với dung lượng não lớn hơn (Scaling Law), mô hình sẽ phân tách ranh giới nhiễu tốt hơn ở các dải xác suất thấp, giúp Win Rate tại Threshold 0.74 vượt mức 80% mà vẫn duy trì được trên 100 tín hiệu.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_CapacityScaling_211'
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
    "TRAINING": {"D_MODEL": 64, "N_HEAD": 8, "NUM_LAYERS": 3, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 80, "LEARNING_RATE": 1e-05,
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

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_211.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_211.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_211).

📊 Kết quả HolyGrail_210:
- Best Val Loss tại Epoch 355. Composite Score: 0.1069
- Win Rate: 78.86% (Threshold 0.74) | 96.96% (Threshold 0.85)

📈 Bảng tổng kết 6 vòng gần nhất (Cấu hình D32, N2, Attention):
| Vòng | Score  | WR@0.74 | WR@0.85 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 210  | 0.1069 | 78.86%  | 96.96%  | N/A     |
(Các vòng trước đã bị hủy bỏ để làm sạch môi trường đếm Overlap)

Nhận định ngắn về xu hướng Score/WR: Vòng 210 (học từ số 0) đã có màn thể hiện xuất sắc, đạt sát mốc 80% (78.86%) ở dải Threshold thấp (0.74) với số lượng tín hiệu dồi dào.
🚀 HolyGrail_211 (PID {pid}) đã kích hoạt! Mục tiêu: Áp dụng Scaling Law (tăng sức mạnh Mạng Neural lên D=64, L=3, H=8) để phá vỡ hoàn toàn rào cản 80% tại Threshold 0.74!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
