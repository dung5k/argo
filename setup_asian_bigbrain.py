# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP BIG BRAIN FOR ASIAN SESSION ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_15m_TP5_SL25_BigBrain_75'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

# Lấy config base của phiên Á
base_cfg_path = r"workspaces\CFG_LTC_ASIAN_V6\runs\run_20260514_074930_v6_ASIAN_5m_W12_TP35_SL15_HolyGrail_40\config.json"
with open(base_cfg_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# --- ÁP DỤNG CÁC Ý TƯỞNG (IDEAS) TỪ PHIÊN LONDON ---
# 1. Não To (Big Brain)
config["TRAINING"]["D_MODEL"] = 128
config["TRAINING"]["N_HEAD"] = 8
config["TRAINING"]["NUM_LAYERS"] = 4
config["TRAINING"]["BATCH_SIZE"] = 128
config["TRAINING"]["DROPOUT"] = 0.30

# 2. Khung Thời Gian 15m & Tầm Nhìn 30 Nến
config["FEATURE_ENGINEERING"]["MTF_INPUTS"] = [
    {
        "SYMBOL": "LTCUSDT",
        "TIMEFRAME": "15min",
        "WINDOW_SIZE": 30,
        "FEATURES": [
            "log_return_close",
            "body_pct",
            "bb_width",
            "rsi_14_scaled",
            "hour_sin",
            "hour_cos"
        ]
    }
]

# 3. Gồng Lệnh Dài (Patience)
config["FEATURE_ENGINEERING"]["MAX_HOLD_BARS"] = 180

# 4. Target Tối Ưu cho Phiên Á (Rộng hơn trước, hẹp hơn London)
config["FEATURE_ENGINEERING"]["TP_PCT"] = 0.005 # 0.5%
config["FEATURE_ENGINEERING"]["SL_PCT"] = 0.0025 # 0.25% (R:R = 1:2)

# Khởi tạo LR nhỏ & Warmup chậm để não to học từ từ
config["TRAINING"]["LEARNING_RATE"] = 2e-5
config["TRAINING"]["WARMUP_EPOCHS"] = 15

config['RUN_ID'] = run_id
config_path = os.path.join(run_dir, 'config.json')

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

# Viết script khởi chạy an toàn
with open('start_train_asian.py', 'w', encoding='utf-8') as f:
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
result = sp.run(["python", "start_train_asian.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- APPEND DIARY CHO ASIAN ----
diary_text = """
### CHIẾN LƯỢC MỚI: KẾ THỪA 'CHÉN THÁNH' LONDON (Ngày 2026-05-14 15:16)
- **Hành động:** Theo lệnh Sếp Lê, đập đi xây lại não Phiên Á bằng cách "vay mượn" 100% chiến thuật đã thành công rực rỡ ở phiên London.
- **Những "Ý tưởng London" được áp dụng:**
  1. **Nâng cấp Não To (Big Brain):** Từ `D32_L2` lên `D128_L4` để mạng có đủ nơ-ron học các vùng kháng cự phức tạp.
  2. **Thay đổi Góc Nhìn:** Dẹp khung `5m`, chuyển thẳng lên khung `15m` với `WINDOW_SIZE = 30` nến. Lọc sạch mọi nhiễu động nhỏ bé của phiên Á.
  3. **Cơ Chế Gồng Trâu:** Nới `MAX_HOLD_BARS` từ 60 lên 180 (cho bot gồng lệnh xuyên suốt 3 tiếng thay vì cắn lén rồi chạy).
  4. **Target Rộng & Cân bằng:** Áp dụng `TP 0.5%` và `SL 0.25%` (R:R 1:2). Mức này rộng gấp đôi so với quá khứ (TP 0.25%), ép bot phải tìm các cú Breakout thực sự thay vì ăn dăm ba pip.
- **Khởi chạy:** Seed 75 (BigBrain_75) đã được kích hoạt ngầm. Mục tiêu: Bứt phá mốc Win Rate 80% với biên độ TP siêu lớn!
"""
with codecs.open('workspaces/CFG_LTC_ASIAN_V6/ASIAN_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [ASIAN V6 MTF] Tạo Run Mới (HolyGrail_75 - KẾ THỪA Ý TƯỞNG LONDON).

Báo cáo Sếp Lê, tôi đã chắt lọc những tinh túy nhất từ chiến thuật London để "Đập đi xây lại" cho phiên Á:

1️⃣ ĐỔI KHUNG NHÌN: Dẹp khung 5m nhiễu loạn, nâng thẳng lên 15m (W30).
2️⃣ NÃO TO: Nâng cấp bộ não lên 128 Chiều (D128), 4 Lớp.
3️⃣ GỒNG LỆNH: Cho phép giữ lệnh tới 180 nến (3 tiếng) thay vì chốt vội.
4️⃣ R:R LỚN: Tăng mục tiêu chốt lời (TP) lên 0.5%, SL 0.25% (Tỷ lệ lợi nhuận 1:2), ép Bot phải bắt sóng lớn, không ăn chắt mót nữa!

Mục tiêu là đập tan mốc Win Rate lẹt đẹt 69% của các vòng trước và tìm ra điểm hội tụ ăn tiền lớn!
🚀 HolyGrail_75 (PID {pid}) mang sức mạnh của "London" đã chính thức kích hoạt trên chiến trường Châu Á!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
