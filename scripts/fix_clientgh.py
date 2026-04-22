import paho.mqtt.client as mqtt
import json, time

c = mqtt.Client()
c.connect('broker.emqx.io', 1883, 60)
c.loop_start()

# Lệnh 1: Dọn dẹp tiến trình cũ (giết mọi Python ngoại trừ MQTT Listener)
cmd_kill = {'cmd': 'run_code', 'code': '''
import os
print("KILLING PREVIOUS TRAIN PROCESSES...")
os.system(r'wmic process where "name=\'python.exe\' and commandline like \'%train_v3.py%\'" call terminate')
'''}
c.publish('argo_dungla_9213/clientGH/cmd', json.dumps(cmd_kill))
time.sleep(2)

# Lệnh 2: Kích hoạt phiên huấn luyện gốc (Cách 1)
cmd_train = {
    'cmd': 'train', 
    'symbol': 'ltcusdt', 
    'script': 'src/training_v3/train_v3.py', 
    'config': 'data/bot_config_ltc_crypto_v3_5.json',
    'scratch': True
}
c.publish('argo_dungla_9213/clientGH/cmd', json.dumps(cmd_train))
time.sleep(2)

# Lệnh 3: Dự phòng chắc chắn (Cách 2 qua run_code)
cmd_force = {'cmd': 'run_code', 'code': '''
import os
repo = os.environ.get('ARGO_REPO', r'C:\\argo')
venv_py = os.environ.get('ARGO_VENV', r'C:\\argo\\venv\\Scripts\\python.exe')
os.system(f'cmd /c "cd /d {repo} && git pull"')
bat_file = os.path.join(repo, 'run_ltc_train.bat')
with open(bat_file, 'w') as f:
    f.write(f'@echo off\\ncd /d "{repo}"\\n"{venv_py}" src/training_v3/train_v3.py data/bot_config_ltc_crypto_v3_5.json\\n')
os.system(f'start /B cmd /c "{bat_file} > train_ltc_bg.log 2>&1"')
'''}
c.publish('argo_dungla_9213/clientGH/cmd', json.dumps(cmd_force))
time.sleep(2)

c.disconnect()
print('Đã dập tắt các tiến trình XAU và ép đào tạo lại LTC!')
