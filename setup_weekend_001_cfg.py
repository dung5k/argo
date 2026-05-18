import os
import json
from datetime import datetime

base_cfg_path = "bot_config_v6_ltc_weekend.json"
with open(base_cfg_path, "r", encoding="utf-8") as f:
    config = json.load(f)

run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}_v6_WE_15m_Win60_Drop10_001"
run_dir = os.path.join("workspaces", "CFG_LTC_WEEKEND_V6", "runs", run_id)
os.makedirs(os.path.join(run_dir, "data", "tensors"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)

# Apply Baseline Search Space for Weekend Seed 001
config["TRAINING"]["LEARNING_RATE"] = 4e-5
config["TRAINING"]["DROPOUT_RATE"] = 0.10
config["TRAINING"]["WARMUP_EPOCHS"] = 15
config["TRAINING"]["BATCH_SIZE"] = 256

config["FEATURE_ENGINEERING"]["TP_PCT"] = 0.005
config["FEATURE_ENGINEERING"]["SL_PCT"] = 0.003
config["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"] = 60

# MTF_INPUTS: LTCUSDT 15min (W60) Baseline
config["FEATURE_ENGINEERING"]["MTF_INPUTS"] = [
    {
        "SYMBOL": "LTCUSDT",
        "TIMEFRAME": "15min",
        "WINDOW_SIZE": 60,
        "FEATURES": [
            "log_return_close",
            "body_pct",
            "bb_width",
            "rsi_14_scaled",
            "hour_sin",
            "hour_cos"
        ]
    }
]

config_out_path = os.path.join(run_dir, "config.json")
with open(config_out_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)

print(run_id)

# Initialize Diary
diary_path = os.path.join("workspaces", "CFG_LTC_WEEKEND_V6", "WEEKEND_V6_DIARY.md")
with open(diary_path, "a", encoding="utf-8") as f:
    f.write(f'''# DIARY LỊCH SỬ HUẤN LUYỆN: CFG_LTC_WEEKEND_V6 MTF

[HỆ THỐNG] Đã thanh lọc toàn bộ dữ liệu huấn luyện cũ theo lệnh Sếp Lê. Hệ thống sẵn sàng cho các vòng huấn luyện mới.

## [Seed 001 - V6 MTF] - Ngày {datetime.now().strftime('%Y-%m-%d')}
### Khởi động kỷ nguyên V6 MTF cho phiên Cuối Tuần

- **Run ID:** {run_id}
- **Bối cảnh:** Bắt đầu áp dụng kiến trúc V6 MTF cho phiên Weekend. Sử dụng Baseline an toàn: LTC 15min với Window 60, Dropout 0.10, tương tự khởi đầu của phiên NY.
- **Mục tiêu:** Thiết lập mốc Win Rate và Score cơ bản để làm bàn đạp cho các bước A/B testing tiếp theo (như Micro-Structure hoặc Leading Indicators).
''')
