import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_dropout_01"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 3:
- **Kết quả:** Kỷ lục Score 0.8958 ở Epoch 52. Win Rate 89.6% (ngưỡng >= 79%) với ~3 lệnh/ngày. Ở ngưỡng >= 70%, WR 70.3% với ~15 lệnh/ngày. Chiến thuật nến 1 phút tỏ ra cực kỳ hoàn hảo cho Micro-Scalping phiên Á.
- **Nhận định:** Đường Validation CE Loss có dấu hiệu tăng dần (overfitting nhẹ) sau Epoch 52. Cần điều chỉnh Regularization.

### Kế hoạch Vòng 4:
- **Hành động:** 
  - Tăng nhẹ Dropout từ 0.05 lên 0.10 để chống Overfitting và giúp model tổng quát hóa tốt hơn.
  - Base Timeframe (1m), TP (0.2%), SL (0.15%), LR (1e-4) được giữ nguyên như Vòng 3 để A/B test độc lập tác động của Dropout.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 3 để kế thừa
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260510_134031_v6_asian_auto_3\config.json'
with open(base_config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
# Tăng dropout
config['TRAINING']['DROPOUT_RATE'] = 0.10

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
print(f"To start: python src/training_v6/train_v6.py workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_ASIAN_V6/runs/{run_id}/train.log 2>&1")
