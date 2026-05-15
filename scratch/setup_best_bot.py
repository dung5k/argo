import json

src_config = r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260510_092600_v6_weekend_continuous_59\config.json'
dest_config = r'd:\DungLA\client1\bot_config_v6_ltc_weekend.json'

with open(src_config, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['INFERENCE'] = {
    'MODEL_PATH': r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260510_092600_v6_weekend_continuous_59\brains\aamt_v3_CFG_LTC_WEEKEND_V6_final.pth',
    'SCALER_PATH': r'd:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs\run_20260510_092600_v6_weekend_continuous_59\brains\scaler_CFG_LTC_WEEKEND_V6.pkl',
    'PROB_THRESHOLD': 0.76
}

# The config also has MT5_PATH, we should preserve it if it exists in the original bot config, but the run's config should already have it.
# Let's ensure the trading path is correct:
config['MT5_PATH'] = r'C:\Program Files\MetaTrader 5\terminal64.exe'

with open(dest_config, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

print("✅ Đã cấu hình bot với mô hình Vòng 59 thành công!")
