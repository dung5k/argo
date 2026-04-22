import paho.mqtt.client as mqtt
import json, time

cmd = {
    'cmd': 'train', 
    'symbol': 'ltcusdt', 
    'script': 'src/training_v3/train_v3.py', 
    'config': 'data/bot_config_ltc_crypto_v3_5.json',
    'scratch': True
}

c = mqtt.Client()
c.connect('broker.emqx.io', 1883, 60)
c.loop_start()
c.publish('argo_dungla_9213/clientGH/cmd', json.dumps(cmd))
time.sleep(2)
c.disconnect()
print('Triggered LTC training on clientGH via pure MQTT format!')
