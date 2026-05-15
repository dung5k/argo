# -*- coding: utf-8 -*-
import os, json, time

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_LONDON_5m_TP8_SL3_Drop30_W15_FarmSeed58'
run_dir = os.path.join('workspaces', 'CFG_LTC_LONDON_V6', 'runs', run_id)

os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

base_config = 'bot_config_v6_ltc.json'
with open(base_config, 'r', encoding='utf-8') as f:
    config = json.load(f)

config['TRAINING']['LEARNING_RATE'] = 5e-5
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['DROPOUT_RATE'] = 0.30
config['TRAINING']['D_MODEL'] = 64
config['TRAINING']['N_HEAD'] = 4
config['TRAINING']['NUM_LAYERS'] = 2

config['FEATURE_ENGINEERING']['SL_PCT'] = 0.003
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.008
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 20

fe_config = config.get('FEATURE_ENGINEERING', {})
if 'MTF_INPUTS' in fe_config and len(fe_config['MTF_INPUTS']) > 0:
    fe_config['MTF_INPUTS'][0]['TIMEFRAME'] = '5min'
    fe_config['MTF_INPUTS'][0]['WINDOW_SIZE'] = 15
    fe_config['MTF_INPUTS'] = [fe_config['MTF_INPUTS'][0]]

config['CONFIG_ID'] = 'CFG_LTC_LONDON_V6'
config['SESSION'] = 'london'
config['SESSION_UTC'] = {"START": "07:00", "END": "13:00"}
config['RUN_ID'] = run_id

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open('start_train.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess\nimport os\n\nrun_id = "{run_id}"\nconfig_path = r"{config_path}"\n\nprint(f"Starting training for {{run_id}}...")\nenv = dict(os.environ, PYTHONIOENCODING="utf-8")\nproc = subprocess.Popen(["python", "-u", "src/training_v6/train_v6.py", config_path, "--run-id", run_id], stdout=open("train_v6_london.log", "w", encoding="utf-8"), stderr=subprocess.STDOUT, env=env)\nprint("Training started in background. PID:", proc.pid)\n''')

print(f'NEW_RUN_ID={run_id}')
