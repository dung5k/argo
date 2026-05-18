import codecs, time, os, json, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 212 (The Regularization Push 212):
- **Kết quả:** Hội tụ tại Epoch 79. Composite Score: **0.0746**. Win Rate: **73.25%** (Threshold 0.71, 86 lệnh) và **87.87%** (Threshold 0.80, 33 lệnh).
- **Phân tích:** Thất bại thảm hại! Việc tăng Dropout lên 0.25 không những không kéo dài được thời gian học (vẫn hội tụ ở Epoch 79) mà còn "bóp nghẹt" nơ-ron, làm giảm trầm trọng năng lực dự đoán. Win Rate và Score rớt thê thảm so với V211. Chứng tỏ với lượng dữ liệu hiện tại, mô hình rất nhạy cảm với việc bị tắt nơ-ron quá mức.

### Ý tưởng tiếp theo (Vòng 213 - The Deep Micro-Architect):
- **Hành động:** Quay xe! Giảm Dropout về mức an toàn và tập trung vào chiều sâu (Depth) thay vì chiều rộng (Width) của mạng.
- **Cấu hình:**
  - Giảm `D_MODEL` về mức 32 (như V210) để tránh dư thừa tham số gây nhiễu.
  - Tăng `NUM_LAYERS` lên 4 (Deep Network) để AI có thể phân giải các hàm logic phi tuyến tính cực kỳ phức tạp từ chuỗi OrderFlow.
  - `N_HEAD` = 8 (Chia nhỏ không gian Attention để quan sát nhiều mẫu hình cùng lúc).
  - Trả `DROPOUT_RATE` về mức 0.15 (an toàn).
  - Giữ nguyên Base TF 5m, Window 24, Fast Hit 5, Attention Pooling, LR=1e-5.
- **Giả thuyết:** Mạng hẹp nhưng sâu (Narrow but Deep) sẽ ép dòng chảy Gradient đi qua nhiều tầng trừu tượng, lọc sạch nhiễu mà không cần dùng Dropout quá cao. Kỳ vọng lấy lại mốc 82% Win Rate của V211 nhưng với số lượng tín hiệu nhiều hơn.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_DeepMicro_213'
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
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 8, "NUM_LAYERS": 4, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 80, "LEARNING_RATE": 1e-05,
                 "DROPOUT_RATE": 0.15, "LR_SCHEDULER": "cosine_warm", "POOLING": "attention"},
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
with open('start_train_asian_213.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_213.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_213).

📊 Kết quả HolyGrail_212:
- Best Val Loss tại Epoch 79. Composite Score: 0.0746
- Win Rate: 73.25% (Threshold 0.71) | 87.87% (Threshold 0.80)

📈 Bảng tổng kết 6 vòng gần nhất (D32, L4, H8, Dropout 0.15):
| Vòng | Score  | WR@0.71 | WR@0.80 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 210  | 0.1069 | 78.86%* | 96.96%* | N/A     |
| 211  | 0.1014 | 82.24%* | 90.00%* | N/A     |
| 212  | 0.0746 | 73.25%  | 87.87%  | N/A     |
(*Các ngưỡng Threshold của 210/211 dao động quanh dải 0.74-0.85)

Nhận định ngắn về xu hướng Score/WR: Vòng 212 thất bại thảm hại! Tăng Dropout lên 0.25 đã bóp nghẹt mạng nơ-ron, làm giảm trầm trọng năng lực học thuật.
🚀 HolyGrail_213 (PID {pid}) đã kích hoạt! Mục tiêu: Quay xe giảm Dropout về 0.15, đồng thời chuyển hướng kiến trúc sang "Mạng Sâu" (D=32, L=4) để ép dòng chảy dữ liệu lọc qua nhiều màng lưới phức tạp hơn!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
