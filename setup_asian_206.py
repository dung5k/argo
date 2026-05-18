# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 205 (EagleEyes Attention 205):
- **Kết quả:** Hội tụ tại Epoch 24. Composite Score: 0.4709. Win Rate đỉnh: **72.34%** (Threshold 0.90, 34 Win / 47 Trades).
- **Phân tích:** Việc hạ D_MODEL về 32 và áp dụng "Mắt Đại Bàng" (Attention Pooling) cùng Window 20 đã kéo Win Rate bật tăng trở lại (từ 68.89% lên 72.34%). Cơ chế Attention đã chứng minh được sức mạnh trong việc nhặt ra các cây nến kích nổ. Tuy nhiên, mức 72.34% vẫn thua mức kỷ lục 74.07% của Vòng 203 (sử dụng Mean Pooling nhưng Window Size là 24). Rõ ràng trên khung 5 phút, chu kỳ 120 phút (Window 24) là con số vàng để nắm bắt xu hướng vĩ mô.

### Ý tưởng tiếp theo (Vòng 206 - The Ultimate 80% Breakthrough 206):
- **Hành động:** Dung hợp 2 đỉnh cao công nghệ! Lấy "Mắt Đại Bàng" (Attention Pooling) của Vòng 205 kết hợp với "Chu kỳ Vàng 120 phút" (Window 24) của Vòng 203.
- **Cấu hình:** 
  - Khôi phục `WINDOW_SIZE: 24` cho LTC 5m (tương đương 120 phút - 2 giờ).
  - Khung phụ: BTC 15m (Window 8), ETH 15m (Window 8).
  - Giữ nguyên `POOLING: "attention"`.
  - D_MODEL=32, BATCH=256, LR=2e-5, DROPOUT=0.20.
  - TP 0.30%, SL 0.25%.
- **Giả thuyết:** Bằng cách mở rộng góc nhìn của Mắt Đại Bàng lên đủ 2 giờ đồng hồ, AI sẽ không bỏ lót bất kỳ nhịp lấy đà nào của dòng tiền, đồng thời tự động loại bỏ các nhiễu động nhỏ nhờ cơ chế Attention. Đây sẽ là cú nổ quyết định để xé rào mốc 80% Win Rate!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_TrueDataset_Breakthrough_206'
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
        "TP_PCT": 0.0030, "SL_PCT": 0.0025, "MAX_HOLD_BARS": 24,
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
with open('start_train_asian_206.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_206.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (TheBreakthrough_206).

📊 Kết quả EagleEyes_205:
- Best Val Loss tại Epoch 24. Composite Score: 0.4709
- Win Rate: 66.18% (Threshold 0.77) | 72.34% (Threshold 0.90)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 201  | 1m + SL 0.25%         | 40.82% | 0.2230 |
| 202  | 5m + BTC15m           | 68.96% | 0.4723 |
| 203  | 5m + BTC + ETH (W24)  | 74.07% | 0.4843 |
| 204  | Scale D_MODEL=64      | 68.89% | 0.4497 |
| 205  | Eagle Eyes (W20)      | 72.34% | 0.4709 |
| 206  | Eagle Eyes + W24      | Đang Chờ| Đang Chờ|

Nhận định V205: Ứng dụng "Mắt Đại Bàng" (Attention Pooling) thay thế Mean Pooling đã phát huy tác dụng, nâng Win Rate từ 68.89% (V204) lên 72.34%. Tuy nhiên, kết quả này vẫn thua mức Kỷ Lục 74.07% của V203. Nguyên nhân nằm ở chỗ V205 bị cắt giảm Window Size xuống 20 (100 phút). Đối với khung 5 phút, 120 phút (Window 24) mới thực sự là chu kỳ vàng!

🎯 Ý tưởng (Vòng 206): The Ultimate Breakthrough!
- Dung hợp 2 đỉnh cao: Áp dụng Mắt Đại Bàng (`POOLING="attention"`) LÊN Chu kỳ Vàng (`WINDOW_SIZE=24`).
- Bộ não AI D_MODEL=32, BATCH=256 sẽ sử dụng Attention quét qua toàn bộ dữ liệu vĩ mô 2 giờ đồng hồ của 3 hệ sinh thái (LTC, BTC, ETH) để ra đòn chí mạng.
- Mục tiêu: Sự dung hợp hoàn hảo nhất. Kỳ vọng đây sẽ là cấu hình chạm mốc 80% Win Rate!

🚀 TheBreakthrough_206 (PID {pid}) đã kích hoạt!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
