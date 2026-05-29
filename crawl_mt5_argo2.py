import sys
import os
import json
from pathlib import Path

# Set ROOT path
_ROOT = Path(r"d:\DungLA\Argo").resolve()
sys.path.insert(0, str(_ROOT))

from scripts.run_simulator import fetch_fresh_data

config_path = _ROOT / "bot_config_v6_xag_asian.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

print("[INFO] Starting MT5 Data Crawl on Argo2 for XAG V6 (150 days)...")
success = fetch_fresh_data(config, days=150)

if success:
    print("[SUCCESS] MT5 data fetched and saved as parquets on Argo2.")
else:
    print("[ERROR] Failed to fetch MT5 data on Argo2.")
