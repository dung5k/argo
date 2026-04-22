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
bg_script = os.path.join(repo, 'bg_train.py')
log_file = os.path.join(repo, 'bg_train.log')

code = f"""
import subprocess
import os
import sys
import paho.mqtt.client as mqtt
import json

repo = r'{repo}'
venv_py = r'{venv_py}'
broker = 'broker.emqx.io'
prefix = 'argo_dungla_9213'
client_id = 'clientGH'

c = mqtt.Client()
try:
    c.connect(broker, 1883, 60)
    c.loop_start()
except:
    pass

def pub_log(msg):
    c.publish(f'{{prefix}}/{{client_id}}/log', json.dumps({{
        'level': 'INFO',
        'message': f'[BG_TRAIN] {{msg}}'
    }}))

def run_cmd(cmd_list, prefix_log):
    pub_log(f'Starting {{prefix_log}}')
    p = subprocess.Popen(cmd_list, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    for line in p.stdout:
        line_clean = line.rstrip()
        pub_log(f'[{{prefix_log}}] {{line_clean}}')
        print(line_clean)
    p.wait()
    pub_log(f'{{prefix_log}} EXIT: {{p.returncode}}')

pub_log('⚡ BEGIN ASYNC TRAINING DETACHED ⚡')

# Pull code first
print('Git pull')
subprocess.run(['git', 'pull'], cwd=repo)

run_cmd([venv_py, 'src/training_v3/train_v3.py', 'data/bot_config_xau_ny_v3_5.json'], 'NY')
run_cmd([venv_py, 'src/training_v3/train_v3.py', 'data/bot_config_xau_london_v3_5.json'], 'LONDON')
pub_log('✅ ALL BG TRAINING DONE')
"""

with open(bg_script, 'w', encoding='utf-8') as f:
    f.write(code)

kwargs = {}
if os.name == 'nt':
    kwargs['creationflags'] = 0x00000008 | 0x00000200

with open(log_file, 'w', encoding='utf-8') as log_f:
    p = subprocess.Popen([venv_py, bg_script], cwd=repo, stdout=log_f, stderr=subprocess.STDOUT, **kwargs)

print(f"🔥 Đã khởi chạy tiến trình huấn luyện ngầm (PID: {p.pid}). Sẽ không bị timeout!")
'''}

c.publish(f'{prefix}/{client_id}/cmd', json.dumps(cmd))
print('Sent: async background train')
time.sleep(2)
c.loop_stop()
c.disconnect()
print('Done!')
