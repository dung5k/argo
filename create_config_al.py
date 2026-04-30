import json
import os

d = 'workspaces/CFG_LTC_NY_V3_5/runs/run_20260429_001200_v3_ny_al'
os.makedirs(d, exist_ok=True)

with open('workspaces/CFG_LTC_NY_V3_5/base_config.json', encoding='utf-8') as f:
    c = json.load(f)

c['TRAINING']['CLS_HEAD'] = 'residual'
c['TRAINING']['LAYER_DROP'] = 0.2

with open(f"{d}/config.json", 'w', encoding='utf-8') as f:
    json.dump(c, f, indent=4)
