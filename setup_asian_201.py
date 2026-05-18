# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Sự cố Vòng 200 (TrueDataset_WideSL_200):
- **Phân tích:** Vòng 200 đã gặp Crash (IndexError) ngay khi vừa nạp dữ liệu. Nguyên nhân là do ở Vòng 199 (có 2 TF: 1m và 15m), script `prepare_v6_dataset.py` đã tạo ra 2 file `X_tf0` và `X_tf1` ở thư mục gốc. Sang Vòng 200 (chỉ có 1 TF), script chỉ ghi đè `X_tf0` mà không xóa `X_tf1` cũ. Sau đó, script copy đã bê nguyên cả `X_tf0` mới và `X_tf1` cũ ném vào thư mục Run. `train_v6.py` đọc nhầm file rác dẫn đến lệch dimension.
- **Giải pháp:** Phải dọn dẹp sạch sẽ (XÓA TRẮNG) thư mục `workspaces/.../data/tensors/` trước khi gọi `prepare_v6_dataset.py`!

### Ý tưởng tiếp theo (Vòng 201 - TrueDataset_WideSL_FIXED_201):
- **Hành động:** Rerun lại nguyên vẹn ý tưởng của Vòng 200 với bản vá Clear Cache Tensor.
- **Cấu hình:** 
  - Single Symbol: LTCUSDT 1m (Window=20).
  - Tích hợp Order Flow (`delta_volume`, `vol_surge_ratio`).
  - TP = 0.0030 (0.3%), SL = 0.0025 (0.25%). (Nới lỏng SL để chống nhiễu vi mô).
  - D_MODEL=32, BATCH=256, LR=2e-5.
- **Giả thuyết:** Với SL 0.25% và sạch bóng dữ liệu rác, AI sẽ cho ra mức Win Rate phản ánh đúng sức mạnh của Order Flow trên khung 1 phút phiên Á.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_TrueDataset_WideSL_FIXED_201'
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
        "TP_PCT": 0.0030, "SL_PCT": 0.0025, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos", "delta_volume", "vol_surge_ratio"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 2e-05,
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
with open('start_train_asian_201.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_201.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Lỗi (HolyGrail_200). Tạo Run Mới (TrueDataset_WideSL_FIXED_201).

📊 Sự cố Vòng 200:
- Vòng 200 bị Crash (IndexError) ngay lúc tải dữ liệu. Nguyên nhân là do hệ thống lưu trữ file Tensor cũ từ nhánh BTC 15m (X_tf1.npy) của vòng 199. Dù Vòng 200 chỉ có 1 Tensor (LTC 1m), nhưng script đã dọn nhầm cả rác cũ vào chung mâm, khiến AI "nhai" nhầm file và nghẹn. Lỗi đã được khắc phục bằng cách làm sạch kho chứa (Wipe Cache) trước khi trích xuất dữ liệu mới.

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 195  | True Match V24        | 56.82%*| 0.3430 |
| 196  | Farming Batch 512     | 55.56%*| 0.3611 |
| 197  | Base TF 5 phút        | 56.82%*| 0.3452 |
| 198  | LeadBTC (Kéo nhầm cũ) | LỖI    | N/A    |
| 199  | LeadBTC + DATA THẬT   | 32.20% | 0.2208 |
| 200  | Crash Tensor          | LỖI    | N/A    |

🎯 Ý tưởng (Vòng 201): Wide SL Rerun!
- Single Symbol: LTCUSDT 1m (Window=20) + Order Flow.
- TP = 0.30%, SL = 0.25% (R:R = 1.2).
- Bằng cách cho lệnh khoảng thở 0.25%, hãy xem liệu Win Rate có phục hồi lên trên mức 50% hay không! Nút thắt của phiên Á chính là Stop Loss.

🚀 TrueDataset_WideSL_FIXED_201 (PID {pid}) đã kích hoạt! Mục tiêu: Tái sinh Win Rate với SL rộng!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
