import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_tf5m"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 6:
- **Kết quả:** Kỷ lục Score đạt 0.8041 (Win Rate 83.3%), cải thiện hơn so với Vòng 5 nhưng chưa đánh bại được Vòng 3.
- **Nhận định:** Việc tăng `WINDOW_SIZE` từ 30 lên 45 giúp mô hình có góc nhìn xa hơn một chút, nhưng vẫn bị kẹt ở khung nến 1 phút với quá nhiều noise nhiễu của phiên Á.

### Kế hoạch Vòng 7:
- **Hành động:** 
  - Thay đổi Base Timeframe từ **1m** lên **5m**.
  - Đặt `WINDOW_SIZE` = **24** (Tương đương 2 tiếng đồng hồ nhìn lùi về quá khứ).
  - Giữ nguyên TP **0.20%**, SL **0.15%**, Dropout **0.05**.
  - Việc chuyển lên nến 5m kỳ vọng sẽ lọc bớt các spike nhiễu (whipsaw) ở khung 1 phút, giúp tín hiệu Micro-Scalping đáng tin cậy hơn.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 6 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260510_154144_v6_asian_win45\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Thay đổi Base Timeframe
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '5min'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 24

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
