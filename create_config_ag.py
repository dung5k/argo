import json
import os

d = 'workspaces/CFG_LTC_NY_V3_5/runs/run_20260428_220500_v3_ny_ag'
os.makedirs(d, exist_ok=True)

with open('workspaces/CFG_LTC_NY_V3_5/base_config.json', encoding='utf-8') as f:
    c = json.load(f)

c['TRAINING']['LEARNING_RATE'] = 5e-5
c['TRAINING']['POOLING'] = 'attention'

with open(f"{d}/config.json", 'w', encoding='utf-8') as f:
    json.dump(c, f, indent=4)
