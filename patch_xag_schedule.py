import json
import os

schedule_path = 'bot_schedule_xag.json'
with open(schedule_path, 'r', encoding='utf-8') as f:
    sched = json.load(f)

runs = {
    'asian': {
        'run_id': 'run_20260515_125021_v5_asian_w20_fh5_attn',
        'config_id': 'CFG_XAG_ASIAN_V5'
    },
    'london': {
        'run_id': 'run_20260516_060355_v5_london_balanced_refiner',
        'config_id': 'CFG_XAG_LONDON_V5'
    },
    'ny': {
        'run_id': 'run_20260510_140500_v5_ny_stable_sniper',
        'config_id': 'CFG_XAG_NY_V5'
    }
}

for session, info in runs.items():
    if session in sched['schedule']:
        sched['schedule'][session]['run_id'] = info['run_id']
        sched['schedule'][session]['config_id'] = info['config_id']
        
        # Read the run's config to sync feature_engineering
        run_config_path = os.path.join('workspaces', info['config_id'], 'runs', info['run_id'], 'config.json')
        if os.path.exists(run_config_path):
            with open(run_config_path, 'r', encoding='utf-8') as rf:
                run_cfg = json.load(rf)
                if 'FEATURE_ENGINEERING' in run_cfg:
                    sched['schedule'][session]['feature_engineering'] = run_cfg['FEATURE_ENGINEERING']

with open(schedule_path, 'w', encoding='utf-8') as f:
    json.dump(sched, f, indent=4)

print("Updated bot_schedule_xag.json")
