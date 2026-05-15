import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_win45"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 5:
- **Kết quả:** Kỷ lục Score đạt 0.7857 (Win Rate 78.5%), tốt hơn Vòng 4 nhưng vẫn thua xa Vòng 3.
- **Nhận định:** Việc siết chặt TP/SL (0.15% / 0.10%) khiến tín hiệu bị nhiễu do spread và noise, khiến mô hình khó ăn hơn so với mức TP 0.20% của Vòng 3. Mức Dropout 0.05 kết hợp TP 0.20% / SL 0.15% vẫn là khung lý tưởng nhất cho nến 1 phút.

### Kế hoạch Vòng 6:
- **Hành động:** 
  - Khôi phục TP về **0.20%**, SL về **0.15%** (giống Vòng 3).
  - Khôi phục Dropout về **0.05** (giống Vòng 3).
  - Tăng **WINDOW_SIZE** của khung Base (1m) từ 30 lên **45** nến. Việc này giúp mô hình nhìn xa hơn một chút (45 phút) để đánh giá cấu trúc sóng trước khi quyết định.
  - Phải chạy lại file `prepare_v6_dataset.py` để sinh tensor mới!
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 5 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260510_151023_v6_asian_tight_tp_sl\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Revert TP/SL
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0020
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0015
# Thay đổi WINDOW_SIZE
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 45

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
