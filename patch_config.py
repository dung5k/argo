import json
import os

config_path = "workspaces/CFG_XAG_NY_V5/runs/run_20260526_220000_v5_ny_liquidity_shield/config.json"

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Update BATCH_SIZE to 32 as requested by Diary
if "TRAIN" not in config:
    config["TRAIN"] = {}
config["TRAIN"]["BATCH_SIZE"] = 32

with open(config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4, ensure_ascii=False)

print(f"Updated BATCH_SIZE to 32 in {config_path}")
