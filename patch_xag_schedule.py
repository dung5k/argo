import json
import os

schedule_file = 'bot_schedule_xag.json'
with open(schedule_file, 'r', encoding='utf-8') as f:
    sched = json.load(f)

# Asian
asian_run = sched['schedule']['asian']['run_id']
with open(os.path.join('workspaces', 'CFG_XAG_ASIAN_V5', 'runs', asian_run, 'config.json'), 'r', encoding='utf-8') as f:
    asian_cfg = json.load(f)
sched['schedule']['asian']['feature_engineering'] = asian_cfg['FEATURE_ENGINEERING']
sched['schedule']['asian']['data_source'] = {'ROUTING': asian_cfg['DATA_SOURCE']['ROUTING']}

# London
london_run = sched['schedule']['london']['run_id']
with open(os.path.join('workspaces', 'CFG_XAG_LONDON_V5', 'runs', london_run, 'config.json'), 'r', encoding='utf-8') as f:
    london_cfg = json.load(f)
sched['schedule']['london']['feature_engineering'] = london_cfg['FEATURE_ENGINEERING']
sched['schedule']['london']['data_source'] = {'ROUTING': london_cfg['DATA_SOURCE']['ROUTING']}

# NY
ny_run = sched['schedule']['ny']['run_id']
with open(os.path.join('workspaces', 'CFG_XAG_NY_V5', 'runs', ny_run, 'config.json'), 'r', encoding='utf-8') as f:
    ny_cfg = json.load(f)
sched['schedule']['ny']['feature_engineering'] = ny_cfg['FEATURE_ENGINEERING']
sched['schedule']['ny']['data_source'] = {'ROUTING': ny_cfg['DATA_SOURCE']['ROUTING']}

with open(schedule_file, 'w', encoding='utf-8') as f:
    json.dump(sched, f, indent=4)
print("Updated bot_schedule_xag.json successfully!")
