import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\LONDON_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_london_tight_tp"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 1:
- **Kết quả:** Thất bại hoàn toàn (Win Rate 0.0%, Early Stopping ở Epoch 31).
- **Nhận định:** Với TP=0.6% và SL=0.4%, việc tìm thấy sóng có biên độ lớn như vậy trong vòng 60 nến là quá khó (dù là phiên London). Quá trình Data Prep đã phải vứt bỏ hơn 171k nến (do `clean_mask`), chỉ giữ lại vỏn vẹn 4,438 mẫu. Mô hình bị đói dữ liệu (Data Starvation) trầm trọng và không thể học được gì.

### Kế hoạch Vòng 2:
- **Hành động:** 
  - Vẫn giữ nguyên quy định R:R = 1.5 của phiên London, nhưng thu hẹp biên độ xuống **TP = 0.3%** (0.003) và **SL = 0.2%** (0.002).
  - Biên độ này thực tế hơn và sẽ giúp tăng lượng dữ liệu Train (Data Samples) lên đáng kể.
  - Các thông số khác giữ nguyên: Khung 1m, `WINDOW_SIZE=45`, `MAX_HOLD_BARS=60`, Dropout=0.05, LR=5e-5.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 1 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs\run_20260510_171821_v6_london_init_v1\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 2
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.003
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.002

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/train.log 2>&1")
