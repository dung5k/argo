import paho.mqtt.client as mqtt
import json, time

broker = 'broker.emqx.io'
prefix = 'argo_dungla_9213'
client_id = 'clientGH'

c = mqtt.Client()
c.connect(broker, 1883, 60)
c.loop_start()

cmd = {'cmd': 'run_code', 'code': '''
import os
import subprocess

repo = os.environ.get('ARGO_REPO', r'D:\\DungLA\\Argo')
venv_py = os.environ.get('ARGO_VENV', r'C:\\argo\\venv\\Scripts\\python.exe')

print('Pulling code...')
subprocess.run(['git', 'pull'], cwd=repo)

bat_content = f"""
@echo off
cd /d "{repo}"
echo [BG] Starting NY Train...
"{venv_py}" src/training_v3/train_v3.py data/bot_config_xau_ny_v3_5.json
echo [BG] Finished NY Train. Starting London Train...
"{venv_py}" src/training_v3/train_v3.py data/bot_config_xau_london_v3_5.json
echo [BG] ALL DONE!
"""

bat_file = os.path.join(repo, 'run_train_bg.bat')
with open(bat_file, 'w') as f:
    f.write(bat_content)

print('Spawning bat file in background...')
os.system(f'start /B cmd /c "{bat_file} > train_v3_bg.log 2>&1"')
print('Background training launched successfully!')
'''}

c.publish(f'{prefix}/{client_id}/cmd', json.dumps(cmd))
print('Sent START /B background method')
time.sleep(2)
c.disconnect()
