import os, json, time, subprocess as sp, codecs

# ==== STATE 0: PHÂN TÍCH ====
# Kết quả FarmSeed 110 (LeadingInd: LTCUSDT 15m + BTCUSDT 15m)
# Epoch 76 | Score 0.0073 | WR@0.64=60.6% | WR@0.69=60.0% | N=30
# Vẫn thất bại — thêm BTCUSDT không giúp Score tăng so với 108/107.
# Nguyên nhân: Có thể Dropout 0.3 đang quá mạnh, cản trở model học correlation.
# --> Kế hoạch Seed 111: Giữ Leading Indicator (LTC + BTC), nhưng giảm Dropout xuống 0.15
#     để model có cơ hội học được mối tương quan BTC->LTC tốt hơn.

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_BTC_Drop15_111'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

# ==== STATE 0: CẬP NHẬT DIARY ====
diary_entry = f"""
### STATE UPDATE: 2026-05-15 17:16
- **Run ID:** {run_id}
- **Kết quả LeadingInd 110:** Thất bại nhẹ - Composite Score 0.0073, WR@0.64=60.6%, WR@0.69=60.0%, N=30. Thêm BTCUSDT vào MTF_INPUTS chưa cải thiện được Score. Model học chậm mối tương quan BTC->LTC.
- **Phân tích nguyên nhân:** Dropout 0.3 quá tích cực đang "phá" các trọng số liên kết chéo giữa 2 encoder. Khi model muốn học "BTC tăng -> LTC tăng trong 15 phút", Dropout lại ngẫu nhiên chặn đứt liên kết này.
- **Kế hoạch Seed 111 (BTC Drop15):** Giữ nguyên cấu trúc MTF 2 mã (LTC 15m + BTC 15m). Giảm Dropout từ 0.3 xuống 0.15 để mạng có thể học được quy luật tương quan. Đây là thử nghiệm kiểm soát đơn biến (Dropout) để isolate hiệu ứng.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_entry)

# ==== STATE 1: TẠO CONFIG RUN 111 ====
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
        "DROPOUT_RATE": 0.15,   # <<< KEY CHANGE: 0.3 -> 0.15
        "LR_SCHEDULER": "cosine_warm"
    },
    "MT5_PATHS": {"BINANCE": "LOCAL"},
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
    "SESSION_UTC": {"START": "07:00", "END": "13:00"},
    "RUN_ID": run_id
}
config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

# ==== STATE 1: KÍCH HOẠT TRAINING ====
import shutil, sys
starter_code = f'''import subprocess, os, sys, shutil
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
root_tensors = "workspaces/CFG_LTC_LONDON_V6/data/tensors"
if os.path.exists(root_tensors):
    for fn in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, fn))

print("[PHASE 1] BUILD TENSORS...", flush=True)
r = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"{config_path}", "--no-upload"], env=env)
if r.returncode != 0:
    print("FATAL: prepare failed"); sys.exit(1)

run_tensors = r"{run_dir}/data/tensors"
os.makedirs(run_tensors, exist_ok=True)
for fn in os.listdir(root_tensors):
    if fn.endswith(".npy") or fn.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, fn), os.path.join(run_tensors, fn))

print("[PHASE 2] START TRAINING...", flush=True)
proc = subprocess.Popen(
    [sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}", "--scratch"],
    stdout=open("train_v6_london.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT, env=env
)
print("PID:", proc.pid)
'''
with open('start_train_london_111.py', 'w', encoding='utf-8') as f:
    f.write(starter_code)

result = sp.run([sys.executable, 'start_train_london_111.py'], capture_output=True, text=True, timeout=30)
pid = "N/A"
for line in result.stdout.split("\n"):
    if "PID:" in line:
        pid = line.split("PID:")[-1].strip()
        break

print(f"Training PID: {pid}")

# ==== GỬI BÁO CÁO TELEGRAM ====
report = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (BTC_Drop15 - Seed 111).

📊 Kết quả LeadingInd Seed 110:
- Best Val Loss tại Epoch 76. Composite Score: 0.0073
- Win Rate: 60.61% (Threshold 0.64) | 60.00% (Threshold 0.69)

📈 Bảng tổng kết 6 vòng gần nhất:
| Seed | Score  | WR@0.75 | WR@0.87 | Hòa Vốn |
|------|--------|---------|---------|---------|
| 106  | 0.2892 | 42.20%  | 50.00%  | 33.3%   |
| 107  | 0.2972 | 43.04%  | 50.00%  | 33.3%   |
| 108  | 0.2964 | 36.71%  | 52.54%  | 33.3%   |
| 109  | 0.0080 | N/A     | N/A     | 33.3%   |
| 110  | 0.0073 | N/A     | 60.00%  | 33.3%   |
| 111  | N/A    | N/A     | N/A     | 33.3%   |

Nhận định: Hai Seed 109-110 đang thất bại do nhiễu loạn khởi tạo + Dropout quá cao chặn học tương quan. Seed 111 giảm Dropout xuống 0.15 để mạng học được quy luật dẫn dắt BTC->LTC.
🚀 Seed 111 (PID {pid}) đã bùng cháy! Mục tiêu: LTC 15m + BTC 15m, Dropout 0.15 — bứt phá lên Score > 0.25!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(report)

sp.run([sys.executable, "scratch/send_tele_wrapper.py", "--done"], check=True)
print("Done.")
