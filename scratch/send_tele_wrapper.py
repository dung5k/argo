import subprocess, sys

with open("scratch/msg.txt", "r", encoding="utf-8") as f:
    msg = f.read()

# Không gán cứng channel, để send_to_tele.py tự lấy phần tử đầu tiên của whitelistChatIds
cmd = ["python", ".agent/send_to_tele.py", msg]
if "--done" in sys.argv:
    cmd.append("--done")
subprocess.run(cmd, check=True)
