# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Sự cố Vòng 198 (TrueDataset_LeadBTC_198):
- **Phân tích:** Vòng 198 đã phát hiện thêm một lỗ hổng chí mạng. Mặc dù script `prepare_v6_dataset.py` ĐÃ TẠO ra Tensor mới ở thư mục gốc (`workspaces/CFG_LTC_ASIAN_V6/data/tensors/`), nhưng script `train_v6.py` lại tìm kiếm file ở thư mục run (`runs/run_xxx/data/tensors/`). Khi không tìm thấy ở thư mục run, `train_v6.py` đã kích hoạt hàm `sync_workspaces.py pull` và **GHI ĐÈ TẤT CẢ** các Tensor mới bằng Tensor cũ kéo từ HuggingFace! 
- **Giải pháp:** Phải chặn đứng cơ chế Pull tự động này bằng cách: Sau khi `prepare_v6_dataset.py` tạo Tensors ở thư mục gốc, hệ thống lập tức **copy toàn bộ Tensor mới** thả vào thư mục `runs/run_xxx/data/tensors/`. Nhờ đó `train_v6.py` sẽ thấy Tensor đã tồn tại và dùng ngay lập tức, bỏ qua hoàn toàn bước Pull HuggingFace!

### Ý tưởng tiếp theo (Vòng 199 - TrueDataset_LeadBTC_FIXED_199):
- **Hành động:** Chạy lại nguyên vẹn cấu hình của Vòng 198 nhưng kèm theo bản vá Lỗi Copy Tensor.
- **Cấu hình:** 
  - Khôi phục Chiến lược Leading Indicator (LTC 1m + BTC 15m).
  - Tích hợp Full Order Flow (`delta_volume`, `vol_surge_ratio`) cho mã chính.
  - TP 0.35%, SL 0.15%, D_MODEL=32, BATCH=256, LR=2e-5.
- **Giả thuyết:** Lần này Data Mới THỰC SỰ được đưa vào não bộ AI. Sự thật về Win Rate của phiên Á sẽ được định đoạt tại đây!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_TrueDataset_LeadBTC_FIXED_199'
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
        "TP_PCT": 0.0035, "SL_PCT": 0.0015, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos", "delta_volume", "vol_surge_ratio"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "15min", "WINDOW_SIZE": 2,
             "FEATURES": ["log_return_close", "body_pct"]}
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
import glob
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"{config_path}", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] INJECT TENSORS INTO RUN DIRECTORY...", flush=True)
run_dir_tensors = r"{run_dir}/data/tensors"
os.makedirs(run_dir_tensors, exist_ok=True)
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"
for f in os.listdir(root_tensors):
    if f.endswith(".npy") or f.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, f), os.path.join(run_dir_tensors, f))
print(f"Copied {{len(os.listdir(run_dir_tensors))}} files into run directory to bypass HF pull!")

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_199.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_199.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (TrueDataset_LeadBTC_FIXED_199).

📊 Sự cố Vòng 198:
Phát hiện thêm một lỗi logic nghiêm trọng trong luồng huấn luyện! Dù `prepare_v6_dataset.py` đã tạo Tensor mới, nhưng `train_v6.py` lại tìm Tensor ở thư mục run trống. Không tìm thấy, nó lập tức kích hoạt kéo dữ liệu từ HuggingFace và **GHI ĐÈ** toàn bộ Tensor mới bằng Tensor cũ! Lỗi này đã được Em vá khẩn cấp: Tự động COPY toàn bộ Tensor mới thả vào thư mục run để Bypass cơ chế Pull rác của hệ thống!

📈 Bảng tổng kết 6 vòng gần nhất (DỮ LIỆU CŨ ẢO ẢNH):
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 192  | Context Only (BTC 15m)| 45.83% | 0.3257 |
| 193  | Single + Order Flow   | 56.82% | 0.3313 |
| 194  | Single + Sai TP/SL    | 56.82% | 0.3383 |
| 195  | True Match V24        | 56.82% | 0.3430 |
| 196  | Farming Batch 512     | 55.56% | 0.3611 |
| 197  | Base TF 5 phút        | 56.82% | 0.3452 |

🎯 Ý tưởng (Vòng 199): Áp dụng Dataset Mới Tinh Hoàn Chỉnh!
- Base Timeframe: 1 phút (Để khai thác Order Flow siêu tốc).
- Leading Indicator: BTCUSDT 15m (W=2) dắt sóng.
- Micro-Features: Bơm thêm `delta_volume`, `vol_surge_ratio` cho LTC.
- R:R Vàng: TP 0.35%, SL 0.15%.
- Lần này, không có bất kỳ dòng dữ liệu rác cũ nào lọt vào não bộ AI!

🚀 TrueDataset_LeadBTC_FIXED_199 (PID {pid}) đã kích hoạt! The show begins now!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
