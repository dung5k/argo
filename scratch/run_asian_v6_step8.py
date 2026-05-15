import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_layerdrop"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 7:
- **Kết quả:** Thất bại hoàn toàn (Win Rate 0.0%, Early Stopping ở Epoch 25).
- **Nhận định:** Khung thời gian 5 phút khiến số lượng sample bị giảm sút nghiêm trọng (chỉ còn ~14,000 mẫu hợp lệ). Khối lượng dữ liệu này là quá ít (Data Starvation) khiến mô hình DualEncoder không thể hội tụ và không dám xuất ra bất kỳ tín hiệu tự tin nào (Max Prob < 0.5).

### Kế hoạch Vòng 8:
- **Hành động:** 
  - Quay trở lại Base Timeframe **1m** với `WINDOW_SIZE` = **30** (Khung vàng của Vòng 3).
  - Giữ nguyên TP **0.20%**, SL **0.15%**, Dropout **0.05** (Khung vàng của Vòng 3).
  - Áp dụng **LAYER_DROP = 0.1**: Kỹ thuật ngẫu nhiên bỏ qua các layer trong lúc train để mô hình bớt học vẹt (Regularization) mà không làm mất mát dữ liệu đầu vào.
  - Learning Rate: **1e-4**.
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
# Revert to 1m
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1m'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 30
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0020
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0015
config['TRAINING']['DROPOUT'] = 0.05
config['TRAINING']['DROPOUT_RATE'] = 0.05
config['TRAINING']['LEARNING_RATE'] = 1e-4
config['TRAINING']['LAYER_DROP'] = 0.1

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
