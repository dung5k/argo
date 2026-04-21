import subprocess
r = subprocess.run(['C:\\\\argo\\\\venv\\\\Scripts\\\\python.exe', 'src/training_v3/train_v3.py', 'workspaces/CFG_LTC_LONDON_V3_5/bot_config_ltc_london_v3_5.json', '--scratch'], capture_output=True, text=True)
print('STDOUT:', r.stdout)
print('STDERR:', r.stderr)