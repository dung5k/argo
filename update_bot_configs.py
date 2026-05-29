import json

configs = {
    "bot_config_v6_ltc_asian.json": "run_20260524_230028_v6_asian",
    "bot_config_v6_ltc_london.json": "run_20260525_011942_v6_london",
    "bot_config_v6_ltc_ny.json": "run_20260525_112308_v3"
}

for filename, run_id in configs.items():
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        data["HF_RUN_ID"] = run_id
        data["RUN_ID"] = run_id
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"Updated {filename} -> {run_id}")
    except Exception as e:
        print(f"Error {filename}: {e}")
