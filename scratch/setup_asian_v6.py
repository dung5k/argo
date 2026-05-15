import os
import shutil
import subprocess

diary_path = r"d:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\ASIAN_V6_DIARY.md"
os.makedirs(os.path.dirname(diary_path), exist_ok=True)

diary_content = """# NHẬT KÝ ĐÀO TẠO - CFG_LTC_ASIAN_V6

## [Run: run_20260510_121000_v6_asian_init_v1] - Ngày 2026-05-10
### Tóm tắt chiến lược: Auto-Tuning Đào Tạo Liên Tục Vòng 1
- **Khởi tạo:** Chuyển đổi kiến trúc sang V6 Heterogeneous MTF (Base 5m, vĩ mô 30m và 1H).
- **Đặc điểm:** Phiên Á thanh khoản mỏng, giá đi ngang.
- **Hành động:** Chạy Vòng 1 với LR=5e-5, Dropout=0.1, Pooling=mean, TP=0.0025, SL=0.0020.
"""

if not os.path.exists(diary_path):
    with open(diary_path, "w", encoding="utf-8") as f:
        f.write(diary_content)
else:
    with open(diary_path, "a", encoding="utf-8") as f:
        f.write("\n" + diary_content)

run_id = "run_20260510_121000_v6_asian_init_v1"
run_dir = os.path.join(r"d:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs", run_id)
os.makedirs(os.path.join(run_dir, "data", "tensors"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "brains"), exist_ok=True)

shutil.copy(r"d:\DungLA\client1\bot_config_v6_ltc_asian.json", os.path.join(run_dir, "config.json"))

print("Run directory created:", run_id)
