import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\LONDON_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_london_init_v1"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Khởi tạo Vòng 1:
- **Mục tiêu:** Thiết lập cấu hình cơ sở (Baseline) cho mô hình LTC Châu Âu V6.
- **Cấu hình:** 
  - Khung Base: **1m**, `WINDOW_SIZE` = **45** (kế thừa kinh nghiệm thành công từ phiên Á).
  - Biên độ rủi ro (London): Thị trường biến động mạnh, nới rộng **TP = 0.6%** (0.006) và **SL = 0.4%** (0.004) để đảm bảo R:R = 1.5 và tránh bị quét râu nến (whipsaw).
  - Giữ nguyên `DROPOUT = 0.05`, `LR = 5e-5`.
  - Tối ưu kích thước mạng: `D_MODEL = 64` (giảm từ 128 mặc định để hội tụ nhanh hơn nhưng vẫn mạnh hơn phiên Á), `NUM_LAYERS = 3`, `BATCH_SIZE = 128`.
  - `MAX_HOLD_BARS` = **60** (thay vì 15) để giá có đủ thời gian chạm TP 0.6%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config gốc làm base
base_config_path = r'd:\DungLA\client1\bot_config_v6_ltc_london.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 1
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1m'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 45
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.006
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.004
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 60

# Training params
config['TRAINING']['DROPOUT'] = 0.05
config['TRAINING']['DROPOUT_RATE'] = 0.05
config['TRAINING']['LEARNING_RATE'] = 5e-05
config['TRAINING']['D_MODEL'] = 64
config['TRAINING']['NUM_LAYERS'] = 3
config['TRAINING']['BATCH_SIZE'] = 128

# Xoá Warning dư thừa nếu có
if "âš ï¸ _STRICT_WARNING_âš ï¸ " in config['FEATURE_ENGINEERING']:
    del config['FEATURE_ENGINEERING']["âš ï¸ _STRICT_WARNING_âš ï¸ "]

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/train.log 2>&1")
