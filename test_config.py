import pandas as pd
import json

with open('workspaces/CFG_LTC_ASIAN_V3_5/runs/run_20260423_221500_v3_asian_1/config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

print(config['FEATURE_ENGINEERING']['MACRO_FEATURES'].keys())
