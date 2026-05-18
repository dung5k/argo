# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 187 (LeadETH1m_D64_187):
- **Kết quả:** Hội tụ tại Epoch 5. Composite Score: 0.3821. Win Rate đỉnh: **56.52%** (Threshold 0.91).
- **Cấu hình:** LTC 1min + ETH 1min + D_MODEL=64.
- **Phân tích:** Việc đổi BTC sang ETH không hề phá vỡ được "bức tường vô hình" 56.52%. Cả 4 biến thể (BTC 1m, BTC 5m, BTC OrderFlow, ETH 1m) đều cho ra Win Rate quanh mức 54-56%. Điều này cho thấy kiến trúc mạng nơ-ron hiện tại đang bị Underfitting (không học được tương quan phức tạp giữa 2 symbol).

### Ý tưởng tiếp theo (Vòng 188 - LeadBTC1m_GiantBrain_188):
- **Hành động:** Quay lại dùng BTCUSDT 1min làm Leading Indicator. Đột phá tăng gấp đôi/gấp ba dung lượng bộ não AI: `D_MODEL` từ 64 lên 128, `N_HEAD` từ 4 lên 8, `NUM_LAYERS` từ 2 lên 4. Kéo dài `WARMUP_EPOCHS` lên 20.
- **Giả thuyết:** Việc kết hợp 2 luồng dữ liệu Tick-by-Tick (1 phút) tạo ra một ma trận siêu phức tạp. "Bức tường 56%" có thể đơn giản là do D_MODEL=64 quá nhỏ để mô hình hóa sự tương quan này. Một bộ não khổng lồ (Giant Brain) như phiên London có thể là chìa khóa giải mã tín hiệu dẫn dắt.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_1m_LeadBTC1m_GiantBrain_188'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

config = {
    "HF_RUN_ID": "run_20260511_210003_v3",
    "MT5_PATH": "C:\\Program Files\\MetaTrader 5 EXNESS\\terminal64.exe",
    "TARGET_SYMBOL": "LTCUSDT", "EXECUTION_SYMBOL": "LTCUSDm", "TARGET_PREFIX": "LTCUSDT",
    "CONFIG_ID": "CFG_LTC_ASIAN_V6", "VERSION": "6.0",
    "HF_CLOUD": {"DATASET_REPO": "dung5k/argo_workspaces", "MODEL_REPO": "dung5k/argo_workspaces", "SYNC_CHUNKS": True},
    "FEATURE_ENGINEERING": {
        "\u26a0\ufe0f_STRICT_WARNING_\u26a0\ufe0f": "T\u1ea4T C\u1ea2 MODULE MACRO_FEATURES L\u00c0 B\u1eaeT BU\u1ed8C.",
        "TP_PCT": 0.0025, "SL_PCT": 0.002, "MAX_HOLD_BARS": 60,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]},
            {"SYMBOL": "BTCUSDT", "TIMEFRAME": "1min", "WINDOW_SIZE": 20,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 128, "N_HEAD": 8, "NUM_LAYERS": 4, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 20, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 1e-05,
                 "DROPOUT_RATE": 0.30, "LR_SCHEDULER": "cosine_warm"},
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
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", r"{config_path}", "--run-id", "{run_id}"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''
with open('start_train_asian_188.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_188.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (LeadBTC1m_GiantBrain_188).

📊 Kết quả V187 (LTC 1m + ETH 1m + D_MODEL 64):
- Best Val Loss tại Epoch 5. Composite Score: 0.3821
- Win Rate: 56.52% (Threshold 0.91) | 50.41% (Threshold 0.78)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 182  | LTC 1m + ETH 5m (D32) | 45.33% | 0.3427 |
| 183  | LTC 1m + BTC 5m (D64) | 54.72% | 0.3584 |
| 184  | LTC 1m + BTC 1m (D64) | 56.25% | 0.3512 |
| 185  | LTC 5m + BTC 5m (D64) | 56.52% | 0.3681 |
| 186  | LTC 1m + BTC 1m (Flow)| 56.25% | 0.3512 |
| 187  | LTC 1m + ETH 1m (D64) | 56.52% | 0.3821 |

Nhận định: Cả 4 phương pháp gép đôi 1m/5m giữa LTC, BTC, ETH đều bị chặn cứng ở "Bức Tường 56%". Có khả năng mô hình đang bị Underfitting do D_MODEL=64 không đủ sức chứa ma trận tương quan giữa 2 đồng coin.

🎯 Ý tưởng mới (Vòng 188): Triệu hồi GIANT BRAIN!
- Sử dụng BTCUSDT 1min làm Leading Indicator.
- Nâng cấp cực đại não bộ AI: `D_MODEL`=128, `N_HEAD`=8, `NUM_LAYERS`=4.
- Tăng `DROPOUT` lên 0.30 và `WARMUP` lên 20 để tránh Overfitting sớm.
- Giảm `LR` xuống 1e-5 để hội tụ mượt mà.
- Giả thuyết: Bộ não lớn hơn sẽ "nuốt" trọn độ nhiễu và tìm ra quy luật dẫn dắt thực sự.

🚀 LeadBTC1m_GiantBrain_188 (PID {pid}) đã kích hoạt! Mục tiêu: Phá vỡ bức tường 56%!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
