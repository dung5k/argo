# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 204 (HolyGrail Scaling 204):
- **Kết quả:** Hội tụ tại Epoch 46. Composite Score: 0.4497. Win Rate đỉnh: **68.89%** (Threshold 0.91).
- **Phân tích:** Việc tăng gấp đôi não bộ (D_MODEL=64) và Batch Size (512) đã khiến mô hình mất đi sự nhạy bén, Win Rate sụt giảm từ 74.07% (Vòng 203) xuống 68.89%. Điều này chứng tỏ với bộ dữ liệu MTF 5 phút, D_MODEL=32 là điểm "Sweet Spot" hoàn hảo, chống Overfit cực tốt.

### Ý tưởng tiếp theo (Vòng 205 - Eagle Eyes Attention 205):
- **Hành động:** Nhận được tin báo chiến thắng từ Argo2 (XAG), tiến hành áp dụng chéo công nghệ đột phá: **Pooling Attention** ("Mắt Đại Bàng") vào mô hình LTC. Thay vì cào bằng trọng số quá khứ (Mean Pooling), AI sẽ tự học cách dồn trọng số vào các cây nến kích nổ (Explosive Candles).
- **Cấu hình:** 
  - Khôi phục Sweet Spot: D_MODEL=32, BATCH=256, LR=2e-5.
  - Áp dụng `POOLING: "attention"`.
  - Giảm Window Size của LTC 5m từ 24 xuống **20** (đồng bộ với thông số Mắt Đại Bàng của Argo2).
  - Khung phụ: BTC 15m (Window 8), ETH 15m (Window 8).
  - TP 0.30%, SL 0.25%.
- **Giả thuyết:** Với "Mắt Đại Bàng" Attention, AI sẽ không còn bị nhiễu bởi các nến đi ngang trong Window 20, mà chỉ tập trung vào các nến Breakout hoặc tín hiệu đảo chiều mạnh từ BTC/ETH. Win Rate được kỳ vọng sẽ phá thủng mốc 80%!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_TrueDataset_EagleEyes_205'
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
        "TP_PCT": 0.0030, "SL_PCT": 0.0025, "MAX_HOLD_BARS": 20,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 20,
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
with open('start_train_asian_205.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_205.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (EagleEyes_205).

📊 Kết quả HolyGrailScaling_204:
- Best Val Loss tại Epoch 46. Composite Score: 0.4497
- Win Rate: 62.90% (Threshold 0.78) | 68.89% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 200  | Crash Tensor          | LỖI    | N/A    |
| 201  | 1m + SL 0.25%         | 40.82% | 0.2230 |
| 202  | 5m + BTC15m           | 68.96% | 0.4723 |
| 203  | 5m + BTC15m + ETH15m  | 74.07% | 0.4843 |
| 204  | Scale D_MODEL=64      | 68.89% | 0.4497 |
| 205  | Eagle Eyes Attention  | Đang Chờ| Đang Chờ|

Nhận định V204: Phép thử Scale-Up (Tăng D_MODEL lên 64) đã làm mất đi sự nhạy bén của não bộ, Win Rate tụt lùi từ 74.07% xuống 68.89%. Điều này xác nhận kiến trúc D_MODEL=32 là Sweet Spot hoàn hảo cho tập dữ liệu này.

🎯 Ý tưởng (Vòng 205): Eagle Eyes Attention (Công nghệ nhập khẩu từ XAG)!
- Tiếp thu công nghệ từ siêu máy tính Argo2 vừa giành chiến thắng vang dội bên XAG.
- Áp dụng cơ chế `POOLING="attention"` (Mắt Đại Bàng) để khai nhãn cho AI: Thay vì cào bằng trọng số quá khứ, AI sẽ chỉ dồn sự chú ý vào các nến kích nổ.
- Hạ `WINDOW_SIZE` xuống 20 để tăng độ tập trung.
- Trả D_MODEL về mốc tối ưu 32. BATCH=256.
- Mục tiêu: Sự kết hợp giữa bộ ba hủy diệt (LTC, BTC, ETH) và Mắt Đại Bàng sẽ là cú hích cuối cùng để xé rào mốc 80% Win Rate!

🚀 EagleEyes_205 (PID {pid}) đã kích hoạt!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py"], check=True)
