# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Tóm tắt Khủng hoảng V209 (Làm sạch hệ thống):
- **Phân tích:** Việc cập nhật `evaluator_v3.py` với `hold_bars` chống đếm lặp tín hiệu đã làm lộ ra sự thật rằng các bộ não cũ (V201 - V208) đã có mức Win Rate bị thổi phồng. Sếp Lê chỉ định: Xóa toàn bộ các bộ não và lịch sử đào tạo cũ (Local + HuggingFace) để không làm vấy bẩn môi trường học tập. Bắt đầu đào tạo lại hoàn toàn từ con số 0.

### Ý tưởng tiếp theo (Vòng 210 - The Clean Slate 210):
- **Hành động:** Khởi tạo lại Mạng Neural (Huấn luyện từ Scratch).
- **Cấu hình:** 
  - Tổng hợp những cấu hình tinh hoa nhất đã được chứng minh: Mắt Đại Bàng (Attention), Chu Kỳ Vàng (W24), Động Lượng (Fast Hit 5), LR=1e-5, Dropout=0.15.
  - Sử dụng cờ `--scratch` để ngăn chặn việc kế thừa tàn dư của quá khứ.
- **Giả thuyết:** Cỗ máy Mạng Neural V210 sẽ là thế hệ đầu tiên được học tập và sát hạch trong một môi trường đánh giá Win Rate trung thực và khắc nghiệt nhất. Từ vòng này trở đi, mọi con số Win Rate đạt được sẽ là "Win Rate Thực Chiến".
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_TrueDataset_CleanSlate_210'
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
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 1e-05,
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
print(f"Copied {{len(os.listdir(run_dir_tensors))}} files into run directory to bypass HF pull!")

print(">>> [PHASE 3] START TRAINING FROM SCRATCH...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_210.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_210.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] XÓA SẠCH VÀ TẠO MỚI (The Clean Slate 210).

📊 Cập nhật trạng thái hệ thống:
- Đã XÓA TOÀN BỘ thư mục `brains/` và `runs/` trên máy tính cục bộ.
- Đã XÓA SẠCH dữ liệu mô hình của nhánh `CFG_LTC_ASIAN_V6` trên HuggingFace Cloud.
- Quá trình kế thừa trọng số cũ đã bị cấm hoàn toàn.

🎯 Ý tưởng (Vòng 210): The Clean Slate!
- Mọi mô hình có "Win Rate ảo" do cơ chế đánh giá cũ đã bị thanh trừng triệt để.
- Khởi tạo bộ não V210 hoàn toàn mới (Đào tạo từ số 0 bằng cờ `--scratch`) nhưng vẫn áp dụng cấu hình xịn nhất (Attention, W24, Fast Hit 5, LR 1e-5).
- Kể từ vòng này, mọi điểm số và Win Rate được báo cáo sẽ là những con số trung thực và khốc liệt nhất (Win Rate Thực Chiến) dưới bộ đếm chống Overlap. Cột mốc 80% sẽ trở nên đắt giá hơn bao giờ hết!

🚀 CleanSlate_210 (PID {pid}) đã kích hoạt từ số không!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
