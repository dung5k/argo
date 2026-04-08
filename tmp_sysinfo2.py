import os, subprocess, sys

print("="*50)
print("TIEN TRINH DANG CHAY (ps -ef / tasklist)")
print("="*50)

if os.name == 'nt':
    r = subprocess.run(["tasklist"], capture_output=True, text=True)
else:
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)

lines = r.stdout.split('\n')
python_procs = [l for l in lines if 'python' in l.lower()]
for p in python_procs:
    print(p[:100])

print("\nKiem tra xem co PID nao dang ket noi/pull HuggingFace khong.")
