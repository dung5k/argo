import psutil, platform, os, datetime, subprocess

print("="*55)
print("KIEM TRA TAI NGUYEN CLIENTGH")
print(f"Thoi gian: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*55)

# CPU
cpu_pct = psutil.cpu_percent(interval=1, percpu=False)
cpu_count = psutil.cpu_count()
print(f"CPU: {cpu_pct:.1f}%  ({cpu_count} cores)")

# RAM
ram = psutil.virtual_memory()
print(f"RAM: {ram.used/1024**3:.1f}/{ram.total/1024**3:.1f} GB  ({ram.percent:.0f}%)")

# DISK
disk = psutil.disk_usage('.')
print(f"Disk: {disk.used/1024**3:.1f}/{disk.total/1024**3:.1f} GB  ({disk.percent:.0f}%)")

# GPU
try:
    import torch
    if torch.cuda.is_available():
        idx = torch.cuda.current_device()
        name = torch.cuda.get_device_name(idx)
        mem_alloc = torch.cuda.memory_allocated(idx)/1024**3
        mem_total = torch.cuda.get_device_properties(idx).total_memory/1024**3
        print(f"GPU: {name}")
        print(f"GPU Mem: {mem_alloc:.2f}/{mem_total:.1f} GB")
    else:
        print("GPU: Khong co / Chua bat")
except Exception as e:
    print(f"GPU: Loi doc ({e})")

# Process Python dang chay
print("\nCac tien trinh Python dang hoat dong:")
for p in psutil.process_iter(['pid','name','cpu_percent','memory_info','cmdline']):
    try:
        if 'python' in p.info['name'].lower():
            cmd = ' '.join(p.info['cmdline'][-3:]) if p.info['cmdline'] else ''
            mem_mb = p.info['memory_info'].rss / 1024**2
            print(f"  PID={p.info['pid']} | RAM={mem_mb:.0f}MB | {cmd[:60]}")
    except: pass

print("="*55)
