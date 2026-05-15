import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\NY_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_ny_win90"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 3:
- **Kết quả:** TIẾP TỤC PHÁ KỶ LỤC! Win Rate cán mốc không tưởng **97.06%** (Score: 0.9706).
- **Nhận định:** Khác với phiên London (nơi 45 nến là điểm cực hạn), phiên New York với đặc thù quét thanh khoản biên độ cực rộng thực sự cần một tầm nhìn dài hơn. Việc kéo giãn `WINDOW_SIZE` lên 60 nến (1 giờ) đã cung cấp đủ ngữ cảnh vĩ mô để AI né được các cú Whipsaw chí tử và tăng tỷ lệ chiến thắng lên một tầm cao mới.

### Kế hoạch Vòng 4:
- **Mục tiêu:** Thừa thắng xông lên, khám phá xem "Điểm Gãy" (Tipping Point) của `WINDOW_SIZE` ở phiên Mỹ nằm ở đâu.
- **Hành động:** 
  - Tiếp tục kế thừa cấu hình Vòng 3 (`BATCH_SIZE=256`, `DROPOUT=0.10`, `TP=0.5%`, `SL=0.3%`).
  - Nới rộng `WINDOW_SIZE` lên mức **90** nến (1.5 tiếng). Đây cũng là thông số đã tạo nên kỷ lục Vô Địch ở phiên Cuối tuần.
  - Lý do: Với biến động khổng lồ của giờ giao thoa Âu - Mỹ, việc quan sát xu hướng của 1.5 giờ trước đó có thể là chiếc chìa khóa cuối cùng để biến mô hình thành một Cỗ Xe Tăng bất khả chiến bại (kỳ vọng WR > 98%).
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 3 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs\run_20260510_200324_v6_ny_win60\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 4
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 90

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_NY_V6/runs/{run_id}/train.log 2>&1")
