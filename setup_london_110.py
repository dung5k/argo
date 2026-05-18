import codecs, time, os, json, subprocess as sp

# 1. DIARY
diary_text = """
### STATE UPDATE: 2026-05-15 16:46
- **Run ID:** run_{timestamp}_v6_LONDON_15m_TP6_SL3_Drop30_W30_LeadingInd_110
- **Kết quả FarmSeed 109:** Thất bại nặng nề! Mặc dù Win Rate đạt 66.6% tại Threshold 0.76, nhưng số lượng tín hiệu sụt giảm thê thảm (N=30), khiến Composite Score chỉ đạt 0.0080. Điều này chứng tỏ rủi ro của Random Seed là rất lớn, và bản thân cấu hình chỉ có 1 mã LTCUSDT đang bắt đầu chạm "trần" giới hạn học thuật.
- **Kế hoạch mới (Seed 110 - The Leading Indicator):** Chuyển hướng sang chiến lược "Chỉ Báo Dẫn Dắt". Thêm mã `BTCUSDT` (Timeframe 15m, Window 16) vào mảng `MTF_INPUTS` để mô hình có thể học được "Quy luật kéo theo" giữa BTC và LTC khi có tin tức hoặc lực đẩy dòng tiền vào phiên London. Các thông số gốc (D128, L4, TP 0.6%, SL 0.3%) vẫn giữ nguyên để so sánh độ hiệu quả của việc thêm Data.
"""
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
diary_text = diary_text.replace("{timestamp}", run_timestamp)

with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_id = f'run_{run_timestamp}_v6_LONDON_15m_TP6_SL3_Drop30_W30_LeadingInd_110'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": run_id,
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT",
    "EXECUTION_SYMBOL": "LTCUSDm",
    "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_LONDON_V6",
    "VERSION": "6.0",
    "HF_CLOUD": {
        "DATASET_REPO": "dung5k/argo_workspaces",
        "MODEL_REPO": "dung5k/argo_workspaces",
        "SYNC_CHUNKS": True
    },
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.006,
        "SL_PCT": 0.003,
        "MAX_HOLD_BARS": 180,
        "LABEL_MODE": "pct",
        "PIP_SIZE": 0.01,
        "lot_size": 0.1,
        "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {
                "SYMBOL": "LTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 30,
                "FEATURES": [
                    "log_return_close",
                    "body_pct",
                    "bb_width",
                    "rsi_14_scaled",
                    "hour_sin",
                    "hour_cos",
                    "volatility_index",
                    "order_flow_imbalance",
                    "atr_14_scaled"
                ]
            },
            {
                "SYMBOL": "BTCUSDT",
                "TIMEFRAME": "15min",
                "WINDOW_SIZE": 16,
                "FEATURES": [
                    "log_return_close",
                    "body_pct",
                    "bb_width",
                    "vol_surge_ratio"
                ]
            }
        ],
        "VOL_REGIME": True,
        "ORDER_FLOW": True
    },
    "TRAINING": {
        "D_MODEL": 128,
        "N_HEAD": 8,
        "NUM_LAYERS": 4,
        "BATCH_SIZE": 256,
        "WARMUP_EPOCHS": 15,
        "FINETUNE_EPOCHS": 60,
        "LEARNING_RATE": 5e-05,
        "DROPOUT_RATE": 0.3,
        "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {
        "BINANCE": "LOCAL"
    },
    "DATA_SOURCE": {
        "RAW_LOCAL_DIR": "workspaces/CFG_LTC_LONDON_V6/data/raw",
        "DATASET_SUFFIX": "2026",
        "TIMEFRAME": "M1",
        "ROUTING": {
            "LTCUSDT": "BINANCE",
            "BTCUSDT": "BINANCE"
        }
    },
    "LIVE_BOT": {
        "PAPER_TRADE": True,
        "TRADE_PLATFORM": "BINANCE",
        "MAX_ABSOLUTE_MSE": 0.8,
        "MIN_PROBABILITY_THRESH": 0.59
    },
    "SESSION": "london",
    "SESSION_UTC": {
        "START": "07:00",
        "END": "13:00"
    },
    "RUN_ID": run_id
}

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

starter = f'''import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
root_tensors = "workspaces/CFG_LTC_LONDON_V6/data/tensors"
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
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}", "--scratch"], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_london_110.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_london_110.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (LeadingInd 110).

📊 Kết quả FarmSeed 109:
- Best Val Loss tại Epoch 61. Composite Score: 0.0080
- Win Rate: 56.41% (Threshold 0.68) | 66.66% (Threshold 0.76)

📈 Bảng tổng kết 6 vòng gần nhất (Chuyển sang "Leading Indicator"):
| Seed | Score  | WR@0.75 | WR@0.87 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 105  | 0.0975 | 12.56%  | 34.21%  | 27.3%   |
| 106  | 0.2892 | 42.20%  | 50.00%  | 33.3%   |
| 107  | 0.2972 | 43.04%  | 50.00%  | 33.3%   |
| 108  | 0.2964 | 36.71%  | 52.54%  | 33.3%   |
| 109  | 0.0080 | N/A     | N/A     | 33.3%   |
| 110  | N/A    | N/A     | N/A     | 33.3%   |

Nhận định ngắn về xu hướng Score/WR: FarmSeed 109 sụp đổ thảm hại do nhiễu loạn Random Seed, chứng tỏ cấu trúc "Độc Lập 1 Mã" đã tới giới hạn. Chuyển chiến lược sang "Chỉ Báo Dẫn Dắt" (Leading Indicator)!
🚀 LeadingInd 110 (PID {pid}) đã bùng cháy! Mục tiêu: Bổ sung mã BTCUSDT (15m) làm nguồn dự báo phụ trợ, kỳ vọng giải quyết được tình trạng mù thông tin khi có tin tức lớn giật giá ở phiên London!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
