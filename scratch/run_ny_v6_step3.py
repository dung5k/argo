import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\NY_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_ny_win60"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 2:
- **Kết quả:** ĐÁNH BẠI KỶ LỤC CŨ! Win Rate đạt **96.97%** (Score: 0.9688) tại ngưỡng 0.73. 
- **Đặc biệt:** Mật độ lệnh duy trì rất ấn tượng (~19.3 lệnh/ngày), cân bằng Buy/Sell (15B/17S) và TUS đạt 0.81.
- **Nhận định:** Quyết định nâng `BATCH_SIZE=256` và `DROPOUT=0.10` là chính xác, giúp mô hình ổn định quá trình hội tụ gradient và tổng quát hóa tốt hơn.

### Kế hoạch Vòng 3:
- **Mục tiêu:** Khám phá thêm khả năng nhìn nhận cấu trúc xu hướng dài hơn của AI trong phiên NY.
- **Hành động:** 
  - Kế thừa cấu hình Vòng 2 (`BATCH_SIZE=256`, `DROPOUT=0.10`, `TP=0.5%`, `SL=0.3%`).
  - Nới rộng `WINDOW_SIZE` từ 45 lên **60** nến (tròn 1 tiếng).
  - Lý do: Mặc dù ở phiên London, việc tăng lên 60 nến không hiệu quả bằng 45, nhưng phiên New York nổi tiếng với các cú quét thanh khoản sâu hơn và trend giật cục kéo dài hơn. Việc nhìn lùi 60 nến có thể cung cấp thêm ngữ cảnh vĩ mô để mô hình tăng tự tin (TUS) và bứt phá tiệm cận WR 98%.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 2 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs\run_20260510_193336_v6_ny_bs256\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 3
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 60

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_NY_V6/runs/{run_id}/train.log 2>&1")
