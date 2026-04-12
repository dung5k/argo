import os, glob, json, time
import paho.mqtt.client as mqtt

def send_mqtt(text):
    try:
        c = mqtt.Client(client_id="fast_probe_999")
        c.connect("broker.emqx.io", 1883, 60)
        c.loop_start()
        c.publish("argo_dungla_9213/clientV2/log", json.dumps({"level": "INFO", "message": text}), qos=0)
        time.sleep(1)
        c.loop_stop()
        c.disconnect()
    except Exception as e:
        print("err:", e)

try:
    runs = glob.glob("runs/*/*.log")
    runs.sort(os.path.getmtime)
    if not runs:
        send_mqtt("NO RUNS Huhu")
        os._exit(0)
    
    last = runs[-1]
    import shutil
    shutil.copyfile(last, "temp_view.log")
    with open("temp_view.log", "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        log_content = "".join(lines[-30:])
        send_mqtt(f"FILE {last}:\n{log_content}")
except Exception as e:
    send_mqtt(f"CRASH: {e}")
