
import paho.mqtt.client as mqtt
import json, time
c = mqtt.Client()
c.connect('broker.hivemq.com', 1883, 60)
code = '''
import glob
for f in glob.glob('*/*/logs/*_unified.log') + glob.glob('*/logs/*_unified.log'):
    try:
        lines = open(f, 'r', encoding='utf-8', errors='replace').readlines()
        print('FILE:', f)
        for val in lines[:4]: print(val.strip())
        print('...')
        for val in list(filter(lambda x: 'CMD' in x or 'TRAIN' in x, lines))[:2]: print(val.strip())
        print('...')
        for val in lines[-4:]: print(val.strip())
    except Exception as e: print(e)
'''
for client in ['clientGH', 'clientEW']:
    c.publish(f'argo_dungla_9213/{client}/cmd', json.dumps({'cmd': 'run_code', 'code': code}))
time.sleep(2)

