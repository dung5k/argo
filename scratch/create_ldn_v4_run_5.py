import os, json, time

run_id = f'run_{time.strftime("%Y%m%d_%H%M%S")}_v4_ldn_5'
run_dir = os.path.join('workspaces', 'CFG_XAG_LDN_V3_5', 'runs', run_id)
os.makedirs(run_dir, exist_ok=True)

with open('workspaces/CFG_XAG_LDN_V3_5/base_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Phẫu thuật siêu cấp theo đúng lệnh: "Ép WINDOW_SIZE cực thấp", "Cắt giảm Neural"
config['FEATURE_ENGINEERING']['TP_PIPS'] = 30
config['FEATURE_ENGINEERING']['SL_PIPS'] = 30
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 8
config['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 10
config['FEATURE_ENGINEERING']['ORDER_FLOW'] = True

# Quay lại với Leaders chuẩn xác có độ thanh khoản M1 cực cao của Exness
config['FEATURE_ENGINEERING']['MACRO_FEATURES'] = {
    "XAUUSDm": ["log_ret", "volume", "bb_width", "corr_60"],
    "USTECm": ["log_ret", "volume", "corr_60"],
    "DXYm": ["log_ret", "volume", "bb_width", "corr_60"]
}
config['DATA_SOURCE']['ROUTING'] = {
    "XAGUSDm": "EXNESS",
    "XAUUSDm": "EXNESS",
    "USTECm": "EXNESS",
    "DXYm": "EXNESS"
}

# Bóp nghẹt não bộ AI để chống học vẹt hoàn toàn
config['TRAINING']['D_MODEL'] = 16
config['TRAINING']['NUM_LAYERS'] = 1
config['TRAINING']['N_HEAD'] = 2
config['TRAINING']['DROPOUT'] = 0.40

with open('workspaces/CFG_XAG_LDN_V3_5/base_config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open(os.path.join(run_dir, 'config.json'), 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open(os.path.join(run_dir, 'tuning_notes_v4.txt'), 'w', encoding='utf-8') as f:
    f.write('Thay đổi: Trở lại với XAU, USTEC, DXY. Ép WINDOW_SIZE xuống 10 nến. Bóp não D_MODEL=16, Dropout=0.40 để bắt AI chỉ được nhìn vào xung lực Market Maker tức thời.\n')

print(run_id)
