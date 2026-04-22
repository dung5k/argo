import os
import subprocess

print("SPAWNING LOCAL LTC TRAINING...")
venv_py = os.environ.get('ARGO_VENV', r'venv\Scripts\python.exe')
cmd = f'start /B cmd /c "{venv_py} src/training_v3/train_v3.py data/bot_config_ltc_crypto_v3_5.json > data/logs/local_ltc_train.log 2>&1"'
os.system(cmd)
print("TRAINING LAUNCHED LOCALLY!")
