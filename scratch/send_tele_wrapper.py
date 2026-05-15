import subprocess

with open("scratch/msg.txt", "r", encoding="utf-8") as f:
    msg = f.read()

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
