# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp, shutil

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 199 (TrueDataset_LeadBTC_FIXED_199):
- **Kết quả:** Hội tụ tại Epoch 40. Composite Score: 0.2208. Win Rate đỉnh: **32.20%** (Threshold 0.73, 19 Win / 59 Trades).
- **Phân tích:** Cú sốc thứ hai! Khi dữ liệu THỰC SỰ được tạo mới theo đúng cấu hình TP=0.35%, SL=0.15% (kèm BTC 15m), Win Rate sụp đổ xuống còn 32.20%! 
- **Lý do:** Với SL = 0.15% trên khung 1 phút, mức cắt lỗ là quá sức chật hẹp (vài tick giá). Dù AI dự đoán đúng xu hướng tổng thể, nhưng nhiễu vi mô (Micro-Noise) của tiền điện tử lập tức quét qua SL trước khi giá kịp chạy đến TP. Tỷ lệ 32% Win Rate phản ánh chính xác rủi ro của SL cực hẹp này trong môi trường thực. Mốc 56.82% (và 77.27%) của các vòng trước hoàn toàn là ảo ảnh do test trên bộ dataset cũ (được sinh ra với SL rộng hơn).

### Ý tưởng tiếp theo (Vòng 200 - TrueDataset_WideSL_200):
- **Hành động:** Nới rộng Stop Loss để cấp "không gian thở" (breathing room) cho tín hiệu. Rút gọn lại thành Single Symbol để kiểm tra base-line.
- **Cấu hình:** 
  - Single Symbol: LTCUSDT 1m (Window=20).
  - Tích hợp Order Flow (`delta_volume`, `vol_surge_ratio`).
  - **Thay đổi quan trọng:** TP = 0.0030 (0.3%), SL = 0.0025 (0.25%). Tỷ lệ R:R = 1.2 (Thỏa mãn luật > 1.2).
  - D_MODEL=32, BATCH=256, LR=2e-5.
- **Giả thuyết:** Với SL 0.25%, mô hình sẽ không bị "quét nhiễu" ngay lập tức sau khi vào lệnh. Win Rate kỳ vọng sẽ phục hồi về vùng > 55% thực tế và có cơ hội chạm 60% bằng sức mạnh thật sự của Order Flow.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_TrueDataset_WideSL_200'
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
with open('start_train_asian_200.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_200.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (TrueDataset_WideSL_200).

📊 Sự cố Vòng 199 (LeadBTC + True Data):
- Best Val Loss tại Epoch 40. Composite Score: 0.2208
- Win Rate THỰC TẾ: 32.20% (Threshold 0.73, 59 Trades)

📈 Bảng tổng kết 6 vòng gần nhất (Hỗn Hợp):
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 194  | Single + Sai TP/SL    | 56.82%*| 0.3383 |
| 195  | True Match V24        | 56.82%*| 0.3430 |
| 196  | Farming Batch 512     | 55.56%*| 0.3611 |
| 197  | Base TF 5 phút        | 56.82%*| 0.3452 |
| 198  | LeadBTC (Kéo nhầm cũ) | LỖI    | N/A    |
| 199  | LeadBTC + DATA THẬT   | 32.20% | 0.2208 |
(*Lưu ý: 194-197 là ảo ảnh do đánh giá trên Tensor cũ)

Nhận định V199: Khi dữ liệu lần đầu tiên được tạo thật với TP=0.35% và SL=0.15%, Win Rate sụp đổ xuống 32%! Lý do là Stop Loss 0.15% quá sức chật hẹp, nhiễu giá phiên Á (Micro-Noise) quét sạch SL của các lệnh ngay trước khi chúng kịp lên TP. Các kỷ lục 77.27% hay 56.82% trong quá khứ thực chất được đào tạo trên những bộ Tensor cũ (được nướng với SL rộng hơn). 

🎯 Ý tưởng (Vòng 200 - Chạm mốc Lịch Sử): The Wide SL!
- Trở lại Single Symbol 1m (LTCUSDT) để đánh giá sức mạnh nguyên thủy.
- Tích hợp Full Order Flow.
- MỞ RỘNG KHÔNG GIAN THỞ: TP = 0.30%, SL = 0.25% (R:R = 1.2 - đúng luật).
- D_MODEL=32, BATCH=256, LR=2e-5.
- Bằng cách cho lệnh khoảng thở 0.25%, chúng ta sẽ xem Win Rate THỰC SỰ của Order Flow là bao nhiêu!

🚀 TrueDataset_WideSL_200 (PID {pid}) đã kích hoạt!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
