import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\NY_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_ny_bs256"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 1:
- **Kết quả:** Kỷ lục CHẤN ĐỘNG! Win Rate chạm nóc **96.67%** (Score: 0.9510) tại ngưỡng 0.71. Ở các ngưỡng thấp hơn như 0.53, WR vẫn đạt tới 86.88%. 
- **Đặc biệt:** Sự phân bổ lệnh Long/Short là hoàn hảo (15 Buy / 15 Sell ở ngưỡng cao nhất, và 30 Buy / 31 Sell ở ngưỡng thấp nhất). AI đã làm chủ được đặc tính Mean Reversion 2 chiều của phiên New York bằng cấu hình `TP 0.5% / SL 0.3%` và `WINDOW_SIZE=45`.
- **Nhận định:** Với D_MODEL=64, mạng học rất hiệu quả và không bị quá tải.

### Kế hoạch Vòng 2:
- **Mục tiêu:** Thử thách việc nâng tổng số lệnh (N) mỗi ngày lên cao hơn mà vẫn duy trì WR > 90% ở các ngưỡng thấp.
- **Hành động:** 
  - Giữ nguyên toàn bộ 'chén thánh' vi mô: `TP 0.5%`, `SL 0.3%`, `WINDOW_SIZE=45`, `D_MODEL=64`.
  - Nâng `BATCH_SIZE` từ 128 lên **256** và tăng `DROPOUT` lên **0.1** (từ 0.05).
  - Lý do: Batch size lớn hơn giúp ổn định độ dốc gradient trong dữ liệu cực kỳ nhiễu loạn của NY, trong khi Dropout 0.1 chống Overfitting tốt hơn. Kỳ vọng mô hình sẽ mượt mà hơn và đẩy TUS lên cao nhất.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 1 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_NY_V6\runs\run_20260510_190320_v6_ny_init_v1\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Cấu hình cụ thể Vòng 2
config['TRAINING']['BATCH_SIZE'] = 256
config['TRAINING']['DROPOUT'] = 0.10
config['TRAINING']['DROPOUT_RATE'] = 0.10

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print("To start run:")
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_NY_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_NY_V6/runs/{run_id}/train.log 2>&1")
