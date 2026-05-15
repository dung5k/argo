import os
import json
import time

run_timestamp = time.strftime('%Y%m%d_%H%M%S')
run_id = f'run_{run_timestamp}_v6_ASIAN_5m_W12_TP35_SL15_HolyGrail_36'
run_dir = os.path.join('workspaces', 'CFG_LTC_ASIAN_V6', 'runs', run_id)

os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, 'data', 'tensors'), exist_ok=True)

base_config = 'bot_config_v6_ltc.json'
with open(base_config, 'r', encoding='utf-8') as f:
    config = json.load(f)

# Fix TRAINING params properly for Asian
config['TRAINING']['LEARNING_RATE'] = 2e-5
config['TRAINING']['WARMUP_EPOCHS'] = 15
config['TRAINING']['DROPOUT_RATE'] = 0.25
config['TRAINING']['D_MODEL'] = 32
config['TRAINING']['N_HEAD'] = 4
config['TRAINING']['NUM_LAYERS'] = 2

# Fix FEATURE_ENGINEERING params
config['FEATURE_ENGINEERING']['SL_PCT'] = 0.002
config['FEATURE_ENGINEERING']['TP_PCT'] = 0.0025
config['FEATURE_ENGINEERING']['MAX_HOLD_BARS'] = 60  # <-- ROOT CAUSE FIX

# Only keep the first MTF input and force it to 1min, W20
fe_config = config.get('FEATURE_ENGINEERING', {})
if 'MTF_INPUTS' in fe_config and len(fe_config['MTF_INPUTS']) > 0:
    fe_config['MTF_INPUTS'][0]['TIMEFRAME'] = '5min'
    fe_config['MTF_INPUTS'][0]['WINDOW_SIZE'] = 12
    fe_config['MTF_INPUTS'] = [fe_config['MTF_INPUTS'][0]] # Remove other timeframes

config['CONFIG_ID'] = 'CFG_LTC_ASIAN_V6'
config['SESSION'] = 'asian'
config['SESSION_UTC'] = {"START": "23:00", "END": "07:00"}
config['RUN_ID'] = run_id

config_path = os.path.join(run_dir, 'config.json')
with open(config_path, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)

with open('start_train.py', 'w', encoding='utf-8') as f:
    f.write(f'''import subprocess\nimport os\n\nrun_id = \"{run_id}\"\nconfig_path = r\"{config_path}\"\nbase_config = \"bot_config_v6_ltc.json\"\n\ntarget_config = config_path if os.path.exists(config_path) else base_config\n\nprint(f\"Starting training for {{run_id}} using {{target_config}}...\")\nenv = dict(os.environ, PYTHONIOENCODING=\"utf-8\")\nproc = subprocess.Popen([\"python\", \"-u\", \"src/training_v6/train_v6.py\", target_config, \"--run-id\", run_id], stdout=open(\"train_v6.log\", \"w\", encoding=\"utf-8\"), stderr=subprocess.STDOUT, env=env)\nprint(\"Training started in background. PID:\", proc.pid)\n''')

print(f'NEW_RUN_ID={run_id}')
