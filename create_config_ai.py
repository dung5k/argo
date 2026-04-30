import json
import os

d = 'workspaces/CFG_LTC_NY_V3_5/runs/run_20260428_231200_v3_ny_ai'
os.makedirs(d, exist_ok=True)

with open('workspaces/CFG_LTC_NY_V3_5/base_config.json', encoding='utf-8') as f:
    c = json.load(f)

c['FEATURE_ENGINEERING']['ORDER_FLOW'] = True
c['FEATURE_ENGINEERING']['VOL_REGIME'] = True

with open(f"{d}/config.json", 'w', encoding='utf-8') as f:
    json.dump(c, f, indent=4)
