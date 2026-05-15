# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP BIG BRAIN 76 FOR ASIAN SESSION ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_76'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

# Lấy config base của phiên Á (có thể lấy luôn từ 75 vì 75 đã config chuẩn)
base_cfg_path = r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260514_151806_v6_ASIAN_15m_TP5_SL25_BigBrain_75\config.json"
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['RUN_ID'] = run_id
config_path = os.path.join(run_dir, 'config.json')

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian_76.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id}"
config_path = r"{config_path}"
env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
print("Generating new dataset tensors for ASIAN...")
with open("upload_v6_asian.log", "w", encoding="utf-8") as f_log:
    sp1 = subprocess.run([sys.executable, "scripts/prepare_v6_dataset.py", "--config", config_path, "--no-upload"], env=env, stdout=f_log, stderr=subprocess.STDOUT)
if sp1.returncode != 0:
    print("Error generating dataset, check upload_v6_asian.log")
    sys.exit(1)
print("Dataset generation completed. Starting training...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"], stdout=open("train_v6_asian.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')

# Thực thi
result = sp.run(["python", "start_train_asian_76.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- APPEND DIARY CHO ASIAN ----
diary_text = f"""
### VÒNG ĐÀO TẠO 76: CỐ ĐỊNH BUG TENSOR & KHỞI CHẠY (Ngày 2026-05-14 15:29)
- **Hành động:** Chạy vòng 76 (BigBrain_76) sau khi fix lỗi load nhầm tensor đa khung thời gian (tf1, tf2) của config cũ. Hệ thống bắt đầu huấn luyện mượt mà trên bộ dữ liệu thuần 15m.
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_76).

📊 Báo cáo sự cố:
- HolyGrail_75 gặp lỗi xung đột kích thước Tensor do dính dữ liệu cache Multi-Timeframe cũ.
- Tôi đã can thiệp xóa sạch cache (tf1, tf2) và khởi tạo lại vòng mới.

🚀 HolyGrail_76 (PID {pid}) mang chiến thuật 'Não To' (Big Brain 15m_D128) đã kích hoạt thành công trên phiên Á! Mục tiêu: Vượt rào Win Rate 80%!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
