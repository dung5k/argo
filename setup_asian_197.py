# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# 1. DIARY
diary_text = """
### Tóm tắt Vòng 196 (SeedFarming_EscapeMinima_196):
- **Kết quả:** Hội tụ tại Epoch 56. Composite Score: 0.3611. Win Rate đỉnh: **55.56%** (Threshold 0.86, 30 Win / 54 Trades).
- **Cấu hình:** Single Symbol, BATCH_SIZE=512, LR=1.2e-5.
- **Phân tích:** Việc thay đổi Batch Size và LR đã thành công bẻ lái quỹ đạo Gradient (số lượng lệnh thay đổi từ 44 sang 54 lệnh), nhưng Win Rate vẫn lơ lửng ở mốc 55.56%. Điều này là một lời khẳng định đanh thép: Trần (Ceiling) giới hạn toán học của mô hình Single Symbol LTC 1 phút trong phiên Á là ~56%. Mọi nỗ lực nhào nặn siêu tham số trên khung 1 phút chỉ là vô nghĩa khi bản chất dữ liệu 1 phút mang quá nhiều nhiễu ngẫu nhiên.

### Ý tưởng tiếp theo (Vòng 197 - SingleSymbol_5m_Shift_197):
- **Hành động:** Sử dụng Đặc quyền "Thay đổi Base Timeframe". Chúng ta sẽ rời bỏ hoàn toàn khung 1 phút (1m) vốn đã bị bào mòn và chứng minh là vô vọng.
- **Cấu hình:**
  - Base Timeframe: **5min** (Làm mượt nhiễu hạt vi mô, nhưng không quá trễ như 15min).
  - Window Size: **24** (120 phút = 2 tiếng ngữ cảnh nến 5m).
  - Single Symbol: LTCUSDT (Không dùng Leading Indicator).
  - Khôi phục tham số: BATCH_SIZE=256, LR=2e-5, D_MODEL=32.
  - TP=0.0035, SL=0.0015 (R:R Vàng).
- **Giả thuyết:** Khung 5 phút sẽ triệt tiêu hoàn toàn các fake-breakout (phá vỡ giả) và thuật toán săn Stop Loss nội bộ của Market Maker trên khung 1 phút. Sự dịch chuyển cấu trúc này là lối thoát duy nhất để phá vỡ bức tường 56%.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# 2. CREATE
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_SingleSymbol_Shift_197'
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
        "TP_PCT": 0.0035, "SL_PCT": 0.0015, "MAX_HOLD_BARS": 24,
        "LABEL_MODE": "pct", "PIP_SIZE": 0.01, "lot_size": 0.1, "CRYPTO_MODE": True,
        "MTF_INPUTS": [
            {"SYMBOL": "LTCUSDT", "TIMEFRAME": "5min", "WINDOW_SIZE": 24,
             "FEATURES": ["log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos"]}
        ],
        "VOL_REGIME": True, "ORDER_FLOW": True
    },
    "TRAINING": {"D_MODEL": 32, "N_HEAD": 4, "NUM_LAYERS": 2, "BATCH_SIZE": 256,
                 "WARMUP_EPOCHS": 15, "FINETUNE_EPOCHS": 60, "LEARNING_RATE": 2e-05,
                 "DROPOUT_RATE": 0.20, "LR_SCHEDULER": "cosine_warm"},
    "MT5_PATHS": {"BINANCE": "LOCAL"},
    "DATA_SOURCE": {"RAW_LOCAL_DIR": "data/history", "DATASET_SUFFIX": "2026", "TIMEFRAME": "M5",
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
with open('start_train_asian_197.py', 'w', encoding='utf-8') as f:
    f.write(starter)

result = sp.run(["python", "start_train_asian_197.py"], capture_output=True, text=True)
pid = result.stdout.strip().split("PID:")[-1].strip() if "PID:" in result.stdout else "N/A"

msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (SingleSymbol_5m_Shift_197).

📊 Kết quả V196 (Seed Farming Batch 512):
- Best Val Loss tại Epoch 56. Composite Score: 0.3611
- Win Rate: 55.56% (Threshold 0.86) | 44.48% (Threshold 0.75)

📈 Bảng tổng kết 6 vòng gần nhất:
| Vòng | Cấu hình              | WR     | Score  |
|------|-----------------------|--------|--------|
| 191  | Base 15m + Lead 15m   | 47.06% | 0.3421 |
| 192  | Context Only (BTC 15m)| 45.83% | 0.3257 |
| 193  | Single + Order Flow   | 56.82% | 0.3313 |
| 194  | Single + Sai TP/SL    | 56.82% | 0.3383 |
| 195  | True Match V24        | 56.82% | 0.3430 |
| 196  | Farming Batch 512     | 55.56% | 0.3611 |

Nhận định: Nỗ lực dùng "Farm Seed" bằng cách đổi Batch Size và LR ở V196 đã thất bại. Mô hình bẻ lái quỹ đạo (đổi số lượng tín hiệu) nhưng Win Rate vẫn chết dí ở 55.56%. Khẳng định: Khung 1 phút (1m) có giới hạn toán học cực đại là ~56% do nhiễu hạt quá cao ở phiên Á. Bất kỳ sự ép buộc nào trên khung 1m cũng chỉ là ảo tưởng.

🎯 Ý tưởng mới (Vòng 197): Dịch Chuyển Trục Thời Gian (Timeframe Shift)!
- Thực thi quyền đổi Base Timeframe: Chuyển toàn bộ hệ thống sang giao dịch trên Khung 5 Phút (5m).
- Bơm 24 nến (120 phút) làm ngữ cảnh (Window_Size=24).
- Khôi phục thông số chuẩn mực: D_MODEL=32, BATCH=256, TP=0.35%, SL=0.15%. (Đồng thời đổi `DATA_SOURCE.TIMEFRAME` thành M5).
- Giả thuyết: Giao dịch Micro-Scalping 1m trong vùng thanh khoản mỏng (Phiên Á) rất dễ dính bẫy thanh khoản. Bằng cách nâng kính lúp lên khung 5m, AI sẽ lọc sạch toàn bộ các nến phá vỡ giả (fake-breakout) 1 phút, mở ra con đường máu để xuyên phá mốc 60%.

🚀 SingleSymbol_5m_Shift_197 (PID {pid}) đã kích hoạt! Mục tiêu: Vượt rào 60% bằng Timeframe 5m!"""

with open("scratch/msg.txt", "w", encoding="utf-8") as f:
    f.write(msg)
sp.run(["python", "scratch/send_tele_wrapper.py", "--done"], check=True)
