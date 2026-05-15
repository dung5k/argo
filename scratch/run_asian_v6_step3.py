import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_auto_3"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 2:
- **Kết quả:** Early Stopping ở Epoch 26. Điểm Score = 0.0, Win Rate = 0%.
- **Nhận định:** Dù đã giảm Dropout và hạ mức TP/SL, mô hình ở TF 5min vẫn không thể tìm được tín hiệu đáng tin cậy trong phiên Á (thanh khoản quá mỏng, sóng quá bé). Cần soi vi mô sâu hơn bằng đồ thị 1 phút (1m).

### Kế hoạch Vòng 3:
- **Hành động:** 
  - Đổi Base Timeframe: 5m -> 1m.
  - Tăng Window Size của 1m lên 30 (nửa tiếng) để bắt trọn vi sóng.
  - Giữ nguyên LR=1e-4, Dropout=0.05.
  - Biên độ TP/SL giữ nguyên (0.0020/0.0015).
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Update config.json from base
with open(r'd:\DungLA\client1\bot_config_v6_ltc_asian.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
config['TRAINING']['DROPOUT_RATE'] = 0.05
config['TRAINING']['LEARNING_RATE'] = 1e-4
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0020
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.0015

# Change base timeframe to 1min
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['TIMEFRAME'] = '1min'
config['FEATURE_ENGINEERING']['MTF_INPUTS'][0]['WINDOW_SIZE'] = 30

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
