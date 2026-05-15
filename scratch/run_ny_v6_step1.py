import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\NY_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_ny_init_v1"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Khởi tạo Vòng 1 (Sau Thanh Trừng):
- **Mục tiêu:** Thiết lập cấu hình cơ sở (Baseline) cho mô hình LTC New York V6 sau khi reset.
- **Cấu hình:** 
  - Khung Base: **1m**, `WINDOW_SIZE` = **45** (áp dụng kinh nghiệm 'sweet spot' từ phiên Á và London).
  - Biên độ rủi ro (NY): Sóng giật 2 chiều cực mạnh, chọn mốc trung bình **TP = 0.5%** (0.005) và **SL = 0.3%** (0.003) để đảm bảo R:R > 1.2 mà vẫn thoát lệnh an toàn.
  - Tối ưu kích thước mạng: Giảm từ cấu trúc gốc nặng nề (`D_MODEL=128`) xuống cấu trúc nhẹ nhàng thực chiến: `D_MODEL=64`, `NUM_LAYERS=3`, `BATCH_SIZE=128`.
  - Nới lỏng `MAX_HOLD_BARS` lên **60** (thay vì 20) để cho phép các lệnh quét 2 chiều có đủ thời gian quay lại chốt lời.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config gốc làm base
base_config_path = r'd:\DungLA\client1\bot_config_v6_ltc_ny.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 1
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1m'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 45
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.005
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
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
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_NY_V6/runs/{run_id}/train.log 2>&1")
