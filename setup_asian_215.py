# -*- coding: utf-8 -*-
import os
import json
import codecs
import time
from datetime import datetime

# Base path is the V214 run config
base_cfg_path = r"workspaces/CFG_LTC_ASIAN_V6/runs/run_20260519_192733_v6_ASIAN_5m_BalancedCapacity_214/config.json"
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Sinh run_id và run_dir cho V215
run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
run_id = f"run_{run_timestamp}_v6_ASIAN_5m_AttentiveSniper_215"
run_dir = os.path.join("workspaces", "CFG_LTC_ASIAN_V6", "runs", run_id)
os.makedirs(os.path.join(run_dir, "data", "tensors"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)

# 1. Áp dụng Search Space mới cho V215: The Attentive Micro-Sniper
config["RUN_ID"] = run_id
config["HF_RUN_ID"] = run_id
config["TRAINING"]["D_MODEL"] = 32
config["TRAINING"]["NUM_LAYERS"] = 3
config["TRAINING"]["N_HEAD"] = 8
config["TRAINING"]["DROPOUT_RATE"] = 0.05       # Tối ưu hóa sâu hơn từ 0.08
config["TRAINING"]["LEARNING_RATE"] = 2.0e-05   # Giúp thoát khỏi cực trị địa phương nhanh hơn khi Dropout cực thấp
config["TRAINING"]["BATCH_SIZE"] = 128          # Tăng tần suất cập nhật gradient mỗi epoch

config_out_path = os.path.join(run_dir, "config.json")
with open(config_out_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

# 2. Cập nhật ASIAN_V6_DIARY.md
diary_file = "workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md"
diary_content = f"""

### Tóm tắt Vòng 214 (The Balanced Capacity Scaler 214):
- **Kết quả:** Hội tụ tại Epoch 356. Composite Score: **0.1373**. Win Rate: **95.70%** (Threshold 0.80, 46 lệnh).
- **Phân tích:** Một bước đột phá cực kỳ ngoạn mục! Mô hình V214 đạt đỉnh **0.1373** (Tăng 28% so với baseline V210 là 0.1069) chứng minh giả thuyết hoàn toàn đúng đắn: Việc hạ thấp Dropout về 0.08 kết hợp với độ sâu hẹp (D=32, L=3) giúp giải phóng dung lượng biểu diễn và tối ưu hoàn hảo trên phiên Á vốn dĩ thanh khoản mỏng.

### Ý tưởng tiếp theo (Vòng 215 - The Attentive Micro-Sniper 215):
- **Hành động:** Tiếp tục mài sắc hơn nữa mô hình tối ưu V214 bằng cách hạ thêm dropout và tinh chỉnh chiến thuật học.
- **Cấu hình:**
  - Giữ `D_MODEL` = 32, `NUM_LAYERS` = 3, `N_HEAD` = 8.
  - Hạ `DROPOUT_RATE` xuống **0.05** để cho phép mô hình bám sát biểu đồ hơn nữa.
  - Tăng `LEARNING_RATE` lên **2.0e-5** (gấp đôi V214) giúp thoát khỏi các điểm yên ngựa (saddle points) nhanh hơn.
  - Đổi `BATCH_SIZE` = 128 giúp mô hình cập nhật trọng số linh động hơn trên tập dữ liệu phiên Á.
- **Giả thuyết:** Với Dropout siêu thấp 0.05 và LR 2.0e-5, mô hình sẽ đạt được độ nhạy cực cao với micro-structures, đẩy Score vượt ngưỡng 0.15 và duy trì tỷ lệ thắng sniper trên 95%.
"""

with codecs.open(diary_file, 'a', encoding='utf-8') as f:
    f.write(diary_content)

# 3. Tạo starter script start_train_asian_215.py
starter_file = "start_train_asian_215.py"
starter = f'''# -*- coding: utf-8 -*-
import subprocess
import os
import sys
import shutil

env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
root_tensors = "workspaces/CFG_LTC_ASIAN_V6/data/tensors"

print(">>> [PHASE 0] CLEAN OLD TENSORS...", flush=True)
if os.path.exists(root_tensors):
    for f in os.listdir(root_tensors):
        os.remove(os.path.join(root_tensors, f))
    print("Cleaned root tensors directory.")

print(">>> [PHASE 0.1] PREPARE RAW DATA PARQUETS...", flush=True)
raw_dir = "workspaces/CFG_LTC_ASIAN_V6/data/raw"
os.makedirs(raw_dir, exist_ok=True)
for sym_file in ["LTCUSDT_2024_2026_M1.parquet", "BTCUSDT_2024_2026_M1.parquet", "ETHUSDT_2024_2026_M1.parquet"]:
    src = os.path.join("data/history", sym_file)
    dst = os.path.join(raw_dir, sym_file)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)
        print(f"Copied {{sym_file}} to raw directory.")

print(">>> [PHASE 1] BUILD TENSOR DATASET...", flush=True)
sp1 = subprocess.run(["C:/argo/venv/Scripts/python.exe", "scripts/prepare_v6_dataset.py", "--config", r"{config_out_path}", "--no-upload"], env=env)
if sp1.returncode != 0:
    print("FATAL ERROR: prepare_v6_dataset failed!")
    sys.exit(1)

print(">>> [PHASE 2] INJECT TENSORS INTO RUN DIRECTORY...", flush=True)
run_dir_tensors = r"{run_dir}/data/tensors"
os.makedirs(run_dir_tensors, exist_ok=True)
for f in os.listdir(root_tensors):
    if f.endswith(".npy") or f.endswith(".pkl"):
        shutil.copy(os.path.join(root_tensors, f), os.path.join(run_dir_tensors, f))

print(">>> [PHASE 3] START TRAINING...", flush=True)
proc = subprocess.Popen(["C:/argo/venv/Scripts/python.exe", "-u", "src/training_v6/train_v6.py", r"{config_out_path}", "--run-id", "{run_id}", "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("PID:", proc.pid)
'''

with open(starter_file, 'w', encoding='utf-8') as f:
    f.write(starter)

print(f"SUCCESS: Created run folder and generated setup config for {run_id}")
