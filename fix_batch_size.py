import json
import glob
import os

configs = glob.glob("D:\\DungLA\\Argo\\bot_config_v6_xag_*.json")
for cfg_file in configs:
    with open(cfg_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    modified = False
    
    # Check WINDOW_SIZE in FEATURE_ENGINEERING
    window_size = 60
    if "FEATURE_ENGINEERING" in data and "WINDOW_SIZE" in data["FEATURE_ENGINEERING"]:
        window_size = data["FEATURE_ENGINEERING"]["WINDOW_SIZE"]
        
    if window_size >= 180:
        if "TRAINING" in data and "BATCH_SIZE" in data["TRAINING"]:
            if data["TRAINING"]["BATCH_SIZE"] > 16:
                print(f"[{os.path.basename(cfg_file)}] WINDOW_SIZE is {window_size}. Reducing BATCH_SIZE from {data['TRAINING']['BATCH_SIZE']} to 16 to prevent OOM.")
                data["TRAINING"]["BATCH_SIZE"] = 16
                modified = True
                
    if modified:
        with open(cfg_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print(f"Saved {cfg_file}")
    else:
        print(f"[{os.path.basename(cfg_file)}] No change needed.")
