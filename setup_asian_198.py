# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 197 (SingleSymbol_5m_Shift_197):
- **Kết quả:** Hội tụ tại Epoch 83. Composite Score: 0.3452. Win Rate đỉnh: **56.82%** (Threshold 0.90, 29 Win / 44 Trades).
- **Phân tích:** Lại một lần nữa Win Rate trả về CHÍNH XÁC 56.82% và có chính xác 44 trades y hệt như khung 1m! Điều này đã làm nổ ra một cuộc điều tra toàn diện vào Source Code.
- **CHÂN TƯỚNG SỰ VIỆC:** Thảm họa Dataset Static! Script `train_v6.py` thực chất KHÔNG tự động generate Tensor mới từ các cấu hình thay đổi (như MTF_INPUTS, Window, Timeframe). Thay vào đó, nó luôn tải lại các Tensors tĩnh (`run_20260511_210003_v3`) đã được bake sẵn và lưu trữ. Toàn bộ 15 vòng A/B Testing vừa qua (từ V183 đến V197) đều là **ảo ảnh**, mô hình train đi train lại trên cùng một bộ dữ liệu 1 phút tĩnh cũ rích! Tất cả thay đổi về Leading Indicators hay Timeframe đều bị bỏ qua hoàn toàn ở bước tiền xử lý!

### Ý tưởng tiếp theo (Vòng 198 - TrueDataset_LeadBTC_198):
- **Hành động:** Khôi phục quyền kiểm soát Pipeline Dữ Liệu! Lần đầu tiên, ta sẽ dùng script `prepare_v6_dataset.py` để TẠO MỚI HOÀN TOÀN Tensors Dữ liệu dựa trên Cấu Hình Mới trước khi đưa vào đào tạo.
- **Cấu hình:** 
  - Khôi phục Chiến lược Leading Indicator (vốn chưa bao giờ thực sự được test).
  - Khung thời gian Base: 1 phút.
  - Tích hợp 2 luồng MTF_INPUTS:
    1. **LTCUSDT (1m):** Lịch sử 20 nến (W=20). Thêm Order Flow (`delta_volume`, `vol_surge_ratio`) để đo áp lực nội tại.
    2. **BTCUSDT (15m):** Lịch sử 2 nến (W=2). Làm kim chỉ nam (Leading Indicator) dắt dẫn xu hướng chung.
  - TP 0.35%, SL 0.15%, D_MODEL=32, BATCH=256, LR=2e-5.
- **Giả thuyết:** Với việc dữ liệu BTC 15m được THỰC SỰ nhúng vào Tensor, AI sẽ bắt đầu học được độ trễ pha (lead-lag) giữa BTC và LTC, phá vỡ định kiến 56% do bộ dataset cũ rích để lại!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_TrueDataset_LeadBTC_198'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": run_id,  # Cập nhật HF_RUN_ID thành ID mới để tránh conflict!
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

starter = f'''import subprocess, os, sys
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", r"{config_path}", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] START TRAINING...", flush=True)
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_198.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_198.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (TrueDataset_LeadBTC_198).

📊 Kết quả V197 (Timeframe 5m Shift):
- Best Val Loss tại Epoch 83. Composite Score: 0.3452
- Win Rate: 56.82% (Threshold 0.90) | 44.65% (Threshold 0.77)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 192  | Context Only (BTC 15m)| 45.83% | 0.3257 |
| 193  | Single + Order Flow   | 56.82% | 0.3313 |
| 194  | Single + Sai TP/SL    | 56.82% | 0.3383 |
| 195  | True Match V24        | 56.82% | 0.3430 |
| 196  | Farming Batch 512     | 55.56% | 0.3611 |
| 197  | Base TF 5 phút        | 56.82% | 0.3452 |

Nhận định Động Trời: Toàn bộ chuỗi A/B Testing từ V183 đến V197 đều là ẢO ẢNH! Script huấn luyện thực chất KHÔNG tự tạo Tensor mới từ JSON Config, mà nó liên tục tải lại file Tensor 1m cũ (`run_20260511_210003_v3`) đã được nướng sẵn. Đó là lý do số lượng lệnh luôn cố định ở 44 và Win Rate kẹt cứng ở 56.82%. Chiến lược Leading Indicator thực chất CHƯA BAO GIỜ được đánh giá đúng nghĩa!

🎯 Ý tưởng mới (Vòng 198): The Great Awakening (Sự thức tỉnh)!
- Ta khôi phục lại chiến lược Leading Indicator (LTC 1m + BTC 15m).
- Chèn thêm Order Flow (`delta_volume`, `vol_surge_ratio`) cho LTC.
- BẮT BUỘC chạy script `prepare_v6_dataset.py` để TẠO MỚI TENSOR trước khi Train.
- Khi dữ liệu BTC 15m THỰC SỰ được nhúng vào Tensors, AI sẽ không còn mù lòa nữa! Mục tiêu là xem AI thực sự làm được gì với Data sạch và đầy đủ ngữ cảnh Vĩ mô.

🚀 TrueDataset_LeadBTC_198 (PID {pid}) đã kích hoạt! Sự thật về Win Rate của phiên Á sẽ được phơi bày!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
