import subprocess
import os

cwd = r"d:\DungLA\client1"

# XAG Bot
cmd_xag = ["python", "src/bot_v3/bot_v3.py", "src/bot_v3/bot_config_xag_base.json", "src/bot_v3/bot_schedule_xag.json"]
# LTC Bot
cmd_ltc = ["python", "src/bot_v3/bot_v3.py", "src/bot_v3/bot_config_ltc_crypto_v3_5.json", "workspaces/shared_meta/bot_v3_brain_schedule_ltc.json"]

CREATE_NEW_CONSOLE = 0x00000010

subprocess.Popen(cmd_xag, cwd=cwd, creationflags=CREATE_NEW_CONSOLE)
subprocess.Popen(cmd_ltc, cwd=cwd, creationflags=CREATE_NEW_CONSOLE)

print("Bots started in new consoles.")
