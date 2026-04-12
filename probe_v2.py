import os, glob, json, time

out = ""
try:
    base_dir = os.environ.get("ARGO_LOGS_DIR", "logs")
    runs_dir = os.path.join(base_dir, "runs")
    out += f"Scanning {runs_dir}:\n"
    if os.path.exists(runs_dir):
        folders = os.listdir(runs_dir)
        out += "\n".join(folders)
    else:
        out += f"Directory {runs_dir} DOES NOT EXIST."
except Exception as e:
    out += f"Error: {e}"

try:
    import paho.mqtt.client as mqtt
    import random
    cid = f"probe_v2_{random.randint(100,999)}"
    client = mqtt.Client(client_id=cid)
    client.connect("broker.emqx.io", 1883, 60)
    client.loop_start()
    
    topic = "argo_dungla_9213/clientV2/log"
    payload = json.dumps({"level": "INFO", "message": f"\n[DIR_LIST] {out}"})
    client.publish(topic, payload, qos=0)
    
    time.sleep(2)
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print("MQTT ERR:", e)
