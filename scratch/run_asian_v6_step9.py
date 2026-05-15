import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_win60"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 8:
- **Kết quả:** Kỷ lục Score 0.7778 (Win Rate 77.7%). Các ngưỡng tự tin cao (WR > 82%) bị phạt TUS cực nặng (Score = 0.0) do phân bổ quá co cụm (TUS < 0.60).
- **Nhận định:** Kỹ thuật `LAYER_DROP = 0.1` và LR=1e-4 không mang lại hiệu quả tích cực. Mô hình không những không thể vượt qua mốc cơ sở (Baseline Vòng 6: Score 0.8041) mà còn bị phạt nặng về độ phân bổ.

### Kế hoạch Vòng 9:
- **Hành động:** 
  - Khôi phục nguyên bản thuật toán của Vòng 6: LR = **5e-5**, `LAYER_DROP` = **0.0**, Base Timeframe **1m**.
  - Đẩy giới hạn bộ nhớ: Tăng `WINDOW_SIZE` lên **60** (tương đương mô hình sẽ nhìn lùi lại trọn vẹn 1 giờ đồng hồ để đọc cấu trúc thị trường). Vòng 6 đã dùng 45 và cải thiện, kỳ vọng 60 sẽ cung cấp bức tranh hoàn chỉnh hơn về vùng Ranging phiên Á.
  - Giữ nguyên thiết lập an toàn: TP **0.20%**, SL **0.15%**, Dropout **0.05**.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config gốc làm base
base_config_path = r'd:\DungLA\client1\bot_config_v6_ltc_asian.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Config Vòng 9
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1m'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 60
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0020
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0015
config['TRAINING']['DROPOUT'] = 0.05
config['TRAINING']['DROPOUT_RATE'] = 0.05
config['TRAINING']['LEARNING_RATE'] = 5e-05
config['TRAINING']['LAYER_DROP'] = 0.0

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
