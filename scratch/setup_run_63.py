import os
import json
import subprocess
import shutil

base_config_path = r"d:\DungLA\client1\bot_config_v6_ltc_weekend.json"
with open(base_config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

# Update parameters
config["FEATURE_ENGINEERING"]["MTF_INPUTS"][0]["TIMEFRAME"] = "5min"
config["FEATURE_ENGINEERING"]["MTF_INPUTS"][0]["WINDOW_SIZE"] = 18
config["TRAINING"]["LEARNING_RATE"] = 5e-05
config["TRAINING"]["DROPOUT_RATE"] = 0.1
config["TRAINING"]["POOLING"] = "mean"

with open(base_config_path, "w", encoding="utf-8") as f:
    json.dump(config, f, indent=4)

print("Updated bot_config_v6_ltc_weekend.json")

run_id = "run_20260510_115800_v6_weekend_continuous_63"
run_dir = os.path.join(r"d:\DungLA\client1\workspaces\CFG_LTC_WEEKEND_V6\runs", run_id)
os.makedirs(run_dir, exist_ok=True)
os.makedirs(os.path.join(run_dir, "data", "tensors"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "results"), exist_ok=True)
os.makedirs(os.path.join(run_dir, "brains"), exist_ok=True)

shutil.copy(base_config_path, os.path.join(run_dir, "config.json"))

print("Run directory created:", run_id)
