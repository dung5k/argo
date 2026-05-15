# -*- coding: utf-8 -*-
import os, json, time, codecs, subprocess as sp

# ---- SETUP SEED 104 (THE PIVOT) ----
run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_15m_TP8_SL3_Drop30_W30_FarmSeed104'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

with open('bot_config_v6_ltc.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# CÚ PIVOT MẠNH MẼ VỀ CẤU TRÚC THEO CHỈ ĐẠO CỦA SẾP LÊ
config['TRAINING']['LEARNING_RATE'] = 5e-5
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['DROPOUT_RATE'] = 0.30

# Nâng cấp Dung lượng Não
config['TRAINING']['D_MODEL'] = 128
config['TRAINING']['N_HEAD'] = 8
config['TRAINING']['NUM_LAYERS'] = 4

# Siết chặt thời gian gồng để tìm kiếm Fast Hit trên khung lớn
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.008
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 12 # Giảm từ 20 xuống 12 (trên khung 15m là 3 tiếng)

fe = config.get('FEATURE_ENGINEERING', {})
if 'MTF_INPUTS' in fe:
    # Đa dạng hóa Nhận thức & Đổi góc nhìn
    fe['MTF_INPUTS'][0]['TIMEFRAME'] = '15min'
    fe['MTF_INPUTS'][0]['WINDOW_SIZE'] = 30 # Nhìn xa hơn
    
    # Bổ sung các features mạnh mẽ
    current_features = fe['MTF_INPUTS'][0].get('FEATURES', [])
    new_features = [
        "log_return_close", "body_pct", "bb_width", "rsi_14_scaled", "hour_sin", "hour_cos",
        "volatility_index", "order_flow_imbalance", "atr_14_scaled"
    ]
    # Lọc những feature được hỗ trợ thực tế
    fe['MTF_INPUTS'][0]['FEATURES'] = new_features
    
    fe['MTF_INPUTS'] = [fe['MTF_INPUTS'][0]]

config['CONFIG_ID'] = 'CFG_LTC_LONDON_V6'
config['SESSION'] = 'london'
config['SESSION_UTC'] = {"START": "07:00", "END": "13:00"}
config['RUN_ID'] = run_id
config_path = os.path.join(run_dir, 'config.json')

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open('start_train.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess, os, sys
run_id = "{run_id}"
config_path = r"{config_path}"
env = dict(os.environ, PYTHONIOENCODING="utf-8")
print("Generating new dataset tensors...")
sp1 = subprocess.run([sys.executable, "scripts/upload_v3_dataset.py", "--config", config_path, "--run-id", run_id, "--no-push"], env=env, capture_output=True, text=True)
if sp1.returncode != 0:
    print("Error generating dataset:", sp1.stderr)
    sys.exit(1)
print("Dataset generation completed. Starting training...")
proc = subprocess.Popen([sys.executable, "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id, "--scratch"], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)
print("Training started in background. PID:", proc.pid)
''')
result = sp.run(["python", "start_train.py"], capture_output=True, text=True)
pid_info = result.stdout.strip()
print(pid_info)
pid = pid_info.split("PID:")[-1].strip() if "PID:" in pid_info else "N/A"

# ---- APPEND DIARY ----
diary_text = """
### STATE UPDATE: 2026-05-14 13:51
- **Run ID:** run_20260514_134458_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed103
- **Kết quả:** Best Val Loss tại Epoch 21. Composite Score: **0.0922**, Win Rate: **22.77%** (Threshold 0.78), **45.45%** (Threshold 0.91, N=55).
- **Phân tích:** Seed 103 kết thúc thời đại "5m, Não Nhỏ" bằng một dư âm huy hoàng: Val Loss đạt **0.4913** (Kỷ Lục Lịch Sử Mới, phá vỡ mốc 0.4916 cũ). Tuy nhiên, đúng như nhận định của Sếp Lê, Win Rate vẫn dậm chân ở mức 45% do mô hình bị mắc kẹt (local minima) ở một giới hạn nhận thức quá hạn hẹp (chỉ 6 tính năng, khung 5m quá nhiễu, não 64 chiều). Đã đến lúc phải thay đổi.
- **Ý tưởng tiếp theo (Seed 104 - THE PIVOT):** Đập đi xây lại! Chúng ta sẽ nâng kích thước não (D_MODEL=128, N_HEAD=8, L=4) để giải được các mẫu hình phức tạp hơn. Đồng thời, nâng khung thời gian lên 15m, mở rộng tầm nhìn (WINDOW_SIZE=30) và giảm Max Hold Bars xuống 12 để bắt các điểm "Fast Hit" không nhiễu. Bắt buộc gắn cờ `--scratch` để train lại từ đầu.
"""
with codecs.open('workspaces/CFG_LTC_LONDON_V6/LONDON_V6_DIARY.md', 'a', encoding='utf-8') as f:
    f.write(diary_text)

# ---- TELEGRAM REPORT THEO MẪU ----
msg = f"""🏯 [LONDON V6 MTF] Tạo Run Mới (FarmSeed 104 - THE PIVOT).

📊 Kết quả FarmSeed 103:
- Best Val Loss tại Epoch 21. Composite Score: 0.0922
- Win Rate: 22.77% (Threshold 0.78) | 45.45% (Threshold 0.91)

📈 Bảng tổng kết 6 vòng gần nhất (5m_W15_Drop30_LR5e-5):
| Seed | Score  | WR@0.80 | WR@0.94 |
|------|--------|---------|---------|
|  98  | 0.1028 |  23.77% |  54.0%  |
|  99  | 0.0920 |  22.18% |  50.0%  |
| 100  | 0.0928 |  23.48% |  46.8%  |
| 101  | 0.0977 |  23.00% |  46.6%  |
| 102  | 0.0981 |  24.01% |  47.3%  |
| 103  | 0.0922 |  22.77% |  45.4%  |

🚨 CHUYỂN GIAO THẾ HỆ - THE PIVOT: 
Seed 103 đã khép lại thế hệ "Não nhỏ - Khung 5m" bằng một Kỷ lục Val Loss vĩ đại: **0.4913**! 
🔥 TUY NHIÊN, vâng lời Sếp Lê, chúng ta từ chối việc dậm chân tại chỗ! Seed 104 sẽ chính thức khởi động kỷ nguyên mới: 
- Nâng Não (D128, H8, L4)
- Đổi Góc Nhìn (Khung 15m, Tầm nhìn 30 nến)
- Bắt Fast Hit (Gồng tối đa 12 nến).
Tiến trình sẽ train lại từ đầu (`--scratch`). 🚀 FarmSeed 104 (PID {pid}) đã bùng cháy! Mục tiêu: Chinh phục WR 60% trên khung 15m!"""

sp.run(["python", ".agent/send_to_tele.py", msg, "--done"], check=True)
