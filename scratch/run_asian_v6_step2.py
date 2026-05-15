import os
import json
import time

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_asian_auto_2"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 1:
- **Kết quả:** Run khởi tạo dừng sớm ở Epoch 24. Điểm Composite Score = 0.0, Win Rate = 0%. Không có tín hiệu giao dịch nào (Abstain 100%).
- **Nhận định:** Mô hình không học được biểu diễn tốt hoặc threshold quá cao so với dao động của phiên Á. Cần giảm Dropout để tăng fit capacity, đồng thời hạ TP/SL xuống để dễ chạm Take Profit hơn.

### Kế hoạch Vòng 2:
- **Hành động:** 
  - Điều chỉnh Dropout: 0.1 -> 0.05
  - Learning Rate: Tăng nhẹ lên 1e-4.
  - TP/SL: Giảm TP xuống 0.0020, SL xuống 0.0015 (R:R=1.33) phù hợp với độ nhiễu thấp phiên Á.
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

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print(f"Created {run_id}")
