import json
with open('workspaces/CFG_LTC_ASIAN_V3_5/base_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
for k in config['FEATURE_ENGINEERING']['MACRO_FEATURES'].keys():
    print(f"'{k}'")
