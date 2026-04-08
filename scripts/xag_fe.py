import sys
import subprocess
print("[TG_AGENT] Bat dau chay Feature Engineering XAGUSD (kem theo file bot_config_xag.json)...")
sys.path.append("src")
subprocess.run([sys.executable, "src/core/feature_engineering.py", "data/bot_config_xag.json"])
print("[TG_AGENT] DONE Feature Engineering!")
