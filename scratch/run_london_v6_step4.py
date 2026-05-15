import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\LONDON_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_london_dropout01"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 3:
- **Kết quả:** Rất tốt nhưng chưa phá được kỷ lục. Win Rate đạt **92.68%** (Score: 0.8038). Early Stopping kích hoạt sớm ở Epoch 42.
- **Nhận định:** Việc kéo giãn `WINDOW_SIZE` lên 60 không giúp mô hình vượt qua được ngưỡng kháng cự của Vòng 2 (`WINDOW_SIZE=45`). Có vẻ 45 nến là điểm cân bằng lý tưởng (sweet spot) giữa độ trễ tín hiệu và tầm nhìn cấu trúc cho phiên London.

### Kế hoạch Vòng 4:
- **Hành động:** 
  - Khôi phục lại `WINDOW_SIZE = 45` như Vòng 2.
  - Tăng `DROPOUT` từ `0.05` lên **`0.10`**.
  - Lý do: Vòng 3 bị Early Stopping khá sớm (Epoch 42). Việc tăng Dropout sẽ ép mạng nơ-ron học các đặc trưng mạnh hơn, giảm phụ thuộc vào các đường nhiễu, từ đó kéo dài thời gian hội tụ và hy vọng đẩy Composite Score vượt mốc 0.8507 của Vòng 2.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 2 làm base (vì nó là kỷ lục)
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs\run_20260510_174823_v6_london_tight_tp\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 4
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 45
config['TRAINING']['DROPOUT'] = 0.10
config['TRAINING']['DROPOUT_RATE'] = 0.10

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/train.log 2>&1")
