import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_tight_tp_sl"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 4:
- **Kết quả:** Kỷ lục Score giảm xuống còn 0.7486 (so với đỉnh 0.8958 ở Vòng 3). Win Rate cao nhất ở ngưỡng 0.74 chỉ đạt 81.8%. Early Stopping kích hoạt sớm ở Epoch 48.
- **Nhận định:** Việc tăng Dropout lên 0.10 đã gây tác dụng phụ, khiến mô hình underfit hoặc không thể học được các mẫu gợn sóng (micro-patterns) cực mỏng trong nến 1 phút của phiên Á. Mức Dropout 0.05 ở Vòng 3 là tối ưu hơn.

### Kế hoạch Vòng 5:
- **Hành động:** 
  - Đưa Dropout quay lại mức tối ưu **0.05**.
  - Áp dụng chiến thuật siết biên độ chốt lời cắt lỗ (Tight TP/SL) để bắt vi sóng trong thị trường ranging:
    - **TP:** Giảm từ 0.20% xuống **0.15%**.
    - **SL:** Giảm từ 0.15% xuống **0.10%**.
  - Tỷ lệ R:R = 1.5 (vẫn tuân thủ điều kiện R:R > 1.2).
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 4 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260510_144033_v6_asian_dropout_01\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Revert dropout
config['TRAINING']['DROPOUT_RATE'] = 0.05
# Adjust TP/SL
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0015
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0010

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print(f"To start: python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
