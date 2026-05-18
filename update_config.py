import json
import os

config_path = 'workspaces/CFG_LTC_LONDON_V6/runs/run_20260518_103900_v6_LONDON_TripleAsset_MicroBatch/config.json'
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['HF_RUN_ID'] = 'run_20260518_103900_v6_LONDON_TripleAsset_MicroBatch'
config['RUN_ID'] = 'run_20260518_103900_v6_LONDON_TripleAsset_MicroBatch'
config['TRAINING']['BATCH_SIZE'] = 32
config['TRAINING']['D_MODEL'] = 64
config['TRAINING']['NUM_LAYERS'] = 3

with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
