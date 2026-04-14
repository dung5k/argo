import subprocess
import paho.mqtt.publish as p
import traceback

print('RUNNING TRAIN')
try:
    proc = subprocess.run(['python', 'src/training_v2/train_v2.py', 'data/bot_config_xau_ny_v2_1.json', '--session', 'ny'], capture_output=True, text=True)
    out = proc.stdout + '\nERR:\n' + proc.stderr
except Exception as e:
    out = traceback.format_exc()

# Gửi output lên kênh MQTT
payload = ('DIAGNOSTIC OUT:\n' + out)[-5000:]
p.single('argo_dungla_9213/clientGH/run_out', payload, hostname='broker.emqx.io')
