import json
import os

d = 'workspaces/CFG_LTC_NY_V3_5/runs/run_20260428_210000_v3_ny_ae'
os.makedirs(d, exist_ok=True)

with open('workspaces/CFG_LTC_NY_V3_5/base_config.json', encoding='utf-8') as f:
    c = json.load(f)

c['FEATURE_ENGINEERING']['WINDOW_SIZE'] = 60
c['TRAINING']['POOLING'] = 'attention'
c['TRAINING']['CLS_HEAD'] = 'residual'
c['FEATURE_ENGINEERING']['ORDER_FLOW'] = False

with open(f"{d}/config.json", 'w', encoding='utf-8') as f:
    json.dump(c, f, indent=4)
