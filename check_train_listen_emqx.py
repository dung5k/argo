import paho.mqtt.client as mqtt
import json, time

def on_connect(c, userdata, flags, rc):
    c.subscribe("argo_dungla_9213/+/log")
    print("Subscribed to EMQX")

def on_message(c, userdata, msg):
    try:
        p = json.loads(msg.payload)
        print(f"[{msg.topic}] {p.get('level')}: {p.get('message')}")
    except Exception as e:
        print(e)
        pass

c = mqtt.Client()
c.on_connect = on_connect
c.on_message = on_message
c.connect("broker.emqx.io", 1883, 60)
c.loop_start()

time.sleep(1)

code = """
import glob, sys, os
try:
    files = glob.glob('*/*/logs/*_unified.log') + glob.glob('*/logs/*_unified.log') + glob.glob('logs/*_unified.log') + glob.glob('*_unified.log')
    res = []
    for f in files:
        lines = open(f, 'r', encoding='utf-8', errors='replace').readlines()
        res.append('FILE: ' + f)
        res.extend([x.strip() for x in lines[:4]])
        res.append('...')
        res.extend([x.strip() for x in list(filter(lambda y: 'CMD' in y or 'TRAIN' in y, lines))[-2:]])
        res.append('...')
        res.extend([x.strip() for x in lines[-4:]])
    if not files: 
        res.append('No _unified.log found in ' + os.getcwd())
    print('\\n'.join(res))
except Exception as e:
    print('ERR:', str(e))
"""
for client in ["clientGH", "clientEW"]:
    c.publish(f"argo_dungla_9213/{client}/cmd", json.dumps({"cmd": "run_code", "code": code}))

time.sleep(15)
c.loop_stop()
