import os, json, time

run_id = f'run_{time.strftime("%Y%m%d_%H%M%S")}_v4_ldn_19'
run_dir = os.path.join('workspaces', 'CFG_XAG_LDN_V3_5', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

with open('workspaces/CFG_XAG_LDN_V3_5/base_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Lượt 19: Cú Bắn Tỉa Tối Thượng (The Ultimate Sniper)
# Ép Window Size xuống cực thấp (10) theo bài học từ Lượt 10 (từng đạt WR 71.8%)
config['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 10

# Bật toàn bộ tính năng SMC (Hướng 2)
config['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
config['FEATURE_ENGINEERING']['VOL_REGIME'] = True

# Giữ nguyên ZERO_NOISE_TARGET (Bài học từ Lượt 17)
config['FEATURE_ENGINEERING']['ZERO_NOISE_TARGET'] = True

# Kiến trúc Neural Tối giản (Minimalist Brain)
config['TRAINING']['D_MODEL'] = 32
config['TRAINING']['NUM_LAYERS'] = 1
config['TRAINING']['N_HEAD'] = 2
config['TRAINING']['DROPOUT'] = 0.4  # Tăng kịch kim để chống học vẹt
config['TRAINING']['LEARNING_RATE'] = 1e-5

# Trở về 3 Leaders Nguyên thủy (XAU, DXY, USTEC)
# VIX và US10Y đã bị loại vì dữ liệu Daily forward-fill gây ra đường thẳng chết trên khung M1
config['FEATURE_ENGINEERING']['MACRO_FEATURES'] = {
    "XAUUSDm": ["log_ret", "volume", "bb_width", "corr_60", "spread_ret", "dxy_xau_anomaly"],
    "USTECm": ["log_ret", "volume", "corr_60", "relative_strength"],
    "DXYm": ["log_ret", "volume", "bb_width", "corr_60", "spread_ret"]
}

# Đảm bảo routing đúng
config['DATA_SOURCE']['ROUTING'] = {
    "XAGUSDm": "EXNESS",
    "XAUUSDm": "EXNESS",
    "USTECm": "EXNESS",
    "DXYm": "EXNESS"
}

config['HF_CLOUD']['SYNC_CHUNKS'] = False

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open(os.path.join(run_dir, 'tuning_notes_v4.txt'), 'w', encoding='utf-8') as f:
    f.write('Thay đổi: Trở lại 3 Leaders nguyên thuỷ. Ép WINDOW_SIZE=10, D_MODEL=32, N_HEAD=2, DROPOUT=0.4. Bật đầy đủ SMC (Order Flow, Vol Regime) + ZERO_NOISE_TARGET.\n')
    f.write('Lý do: Lượt 18 sập Win Rate vì dữ liệu VIX/US10Y từ Yahoo Finance là Daily (D1) được forward-fill xuống khung phút (M1) tạo ra một đường thẳng dài 1440 nến, không có giá trị dự đoán intraday. Lượt 10 từng đạt 71.8% với WINDOW_SIZE=10. Giờ ta sẽ kết hợp bộ khung Lượt 10 với ZERO_NOISE_TARGET của Lượt 17 và bơm thêm SMC Footprints để hoàn thiện Cú Bắn Tỉa.\n')
    f.write('Kỳ vọng: Hội tụ toàn bộ những điểm tinh hoa nhất từ Lượt 10 và Lượt 17 để đục thủng 80% Win Rate.\n')

print(run_id)
