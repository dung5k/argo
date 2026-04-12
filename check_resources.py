import subprocess, sys
smi = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.used,memory.free,memory.total,utilization.gpu",
                      "--format=csv,noheader,nounits"], capture_output=True, text=True)
print("GPU Status:")
print(smi.stdout.strip())
name, used, free, total, util = [x.strip() for x in smi.stdout.strip().split(',')]
print(f"\nVRAM: {used}MB / {total}MB dùng ({int(used)/int(total)*100:.1f}%)")
print(f"VRAM còn lại: {free}MB ({int(free)/int(total)*100:.1f}%)")
print(f"GPU Utilization: {util}%")

import psutil
ram = psutil.virtual_memory()
print(f"\nRAM: {ram.used//1024//1024}MB / {ram.total//1024//1024}MB ({ram.percent}%)")
cpu = psutil.cpu_percent(interval=1)
print(f"CPU: {cpu}%")
