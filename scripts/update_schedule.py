import json
import os

schedule_path = 'bot_schedule_v6_ltc.json'
run_config_path = r'workspaces\CFG_LTC_LONDON_V6\runs\run_20260518_110900_v6_LONDON_TripleAsset_Fast\config.json'

with open(schedule_path, 'r', encoding='utf-8') as f:
    schedule = json.load(f)

with open(run_config_path, 'r', encoding='utf-8') as f:
    run_config = json.load(f)

for k in schedule['schedule'].keys():
    if k.lower() == 'london':
        london_key = k
        break

schedule['schedule'][london_key]['run_id'] = run_config['HF_RUN_ID']
schedule['schedule'][london_key]['feature_engineering'] = run_config['FEATURE_ENGINEERING']
schedule['schedule'][london_key]['training'] = run_config['TRAINING']

if 'trading_config' not in schedule['schedule'][london_key]:
    schedule['schedule'][london_key]['trading_config'] = {}
schedule['schedule'][london_key]['trading_config']['min_prob_thresh'] = 0.92

with open(schedule_path, 'w', encoding='utf-8') as f:
    json.dump(schedule, f, indent=4)

print("Updated bot_schedule_v6_ltc.json for London session!")
