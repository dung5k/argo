import os
import sys

def probe():
    print(f"OS Name: {os.name}")
    print(f"ARGO_DATA_DIR env: {os.environ.get('ARGO_DATA_DIR')}")
    import json
    cfg_file = "data/bot_config_xau_asian_v2.json"
    if os.path.exists(cfg_file):
        with open(cfg_file, "r") as f:
            cfg = json.load(f)
            print(f"ARGO_DATA_DIR in cfg: {cfg.get('ARGO_DATA_DIR')}")
    else:
        print("config NOT FOUND")

if __name__ == "__main__":
    probe()
