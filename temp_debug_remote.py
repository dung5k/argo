import os
import glob
import json
import urllib.request
from pathlib import Path

def telegram_log(msg):
    try:
        cfg_path = Path("tg_config.json")
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text("utf-8"))
            token = cfg.get("bot_token")
            cid = cfg.get("chat_id")
            if token and cid:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                data = json.dumps({"chat_id": cid, "text": f"[DEBUG clientV2]\n{msg}"}).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=5)
    except:
        print(f"TELEGRAM ERR: {msg}")

out = "Check data:\n"
data_dir = Path("data")
if data_dir.exists():
    for f in data_dir.glob("*_CFG_XAU_ASIAN_V2*"):
        sz = f.stat().st_size / (1024*1024)
        out += f"{f.name} = {sz:.2f} MB\n"

out += "\nCheck runs logs:\n"
import glob
runs = glob.glob("runs/*/*.log")
runs.sort(key=os.path.getmtime)
if runs:
    with open(runs[-1], "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        out += f"{runs[-1]}:\n"
        out += "".join(lines[-20:])

telegram_log(out)
