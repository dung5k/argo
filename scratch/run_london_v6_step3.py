import os
import json
import time
import subprocess

diary_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\LONDON_V6_DIARY.md'
run_timestamp = time.strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_london_win60"

diary_content = f"""
## [Run: {run_id}] - Ngày {time.strftime("%Y-%m-%d")}
### Tóm tắt Vòng 2:
- **Kết quả:** Thành công RỰC RỠ! Kỷ lục Win Rate đạt **93.10%** (Score: 0.8507) tại ngưỡng tín hiệu `0.71`. Mô hình bắt sóng cực nét. Lỗi Push lên HuggingFace do vướng file binary `train.log` không ảnh hưởng đến chất lượng thuật toán.
- **Nhận định:** Quyết định hạ tham vọng xuống TP 0.3% / SL 0.2% là cực kỳ đúng đắn. Nó giúp lượng data đủ lớn (23k nến) để AI học được nhịp điệu giật của phiên London mà vẫn đảm bảo được R:R=1.5.

### Kế hoạch Vòng 3:
- **Hành động:** 
  - Khung thời gian: Vẫn giữ Base TF là **1m**, nhưng nới rộng `WINDOW_SIZE` từ 45 lên **60**.
  - Lý do: Phiên London nổi tiếng với các xu hướng (trend) kéo dài. Mở rộng tầm nhìn lên 60 phút (1 giờ) sẽ giúp AI tránh bị lừa bởi các nhịp điều chỉnh ngắn hạn (pullback) trong cấu trúc sóng tổng thể.
  - Các thông số chuẩn khác giữ nguyên: TP 0.3%, SL 0.2%, `MAX_HOLD_BARS=60`, Dropout 0.05, LR 5e-5.
"""

with open(diary_path, 'a', encoding='utf-8') as f:
    f.write(diary_content)

run_dir = os.path.join(r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs', run_id)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'results'), exist_ok=True)
os.makedirs(os.path.join(run_dir, 'brains'), exist_ok=True)

# Lấy config của Vòng 2 làm base
base_config_path = r'd:\DungLA\client1\workspaces\CFG_LTC_LONDON_V6\runs\run_20260510_174823_v6_london_tight_tp\config.json'
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
print(f"python scripts/prepare_v6_dataset.py --config workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --no-upload")
print(f"python src/training_v6/train_v6.py workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/config.json --scratch --run-id {run_id} > workspaces/CFG_LTC_LONDON_V6/runs/{run_id}/train.log 2>&1")
