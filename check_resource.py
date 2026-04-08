import psutil
import torch
import shutil

def main():
    print("=== TÌNH TRẠNG TÀI NGUYÊN CLIENT ===")
    
    # 1. CPU & RAM
    cpu_percent = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    total_ram_gb = ram.total / (1024**3)
    used_ram_gb = ram.used / (1024**3)
    free_ram_gb = ram.available / (1024**3)
    
    print(f"🖥 CPU Usage : {cpu_percent}%")
    print(f"🧠 RAM Usage : {used_ram_gb:.1f}GB / {total_ram_gb:.1f}GB (Trống: {free_ram_gb:.1f}GB - {100-ram.percent:.1f}%)")
    
    # 2. DISK
    disk = shutil.disk_usage(".")
    print(f"💾 Disk Free : {disk.free / (1024**3):.1f}GB (Tổng: {disk.total / (1024**3):.1f}GB)")
    
    # 3. GPU
    print("🎮 GPU Status:")
    if torch.cuda.is_available():
        count = torch.cuda.device_count()
        for i in range(count):
            name = torch.cuda.get_device_name(i)
            mem_allocated = torch.cuda.memory_allocated(i) / (1024**3)
            mem_reserved = torch.cuda.memory_reserved(i) / (1024**3)
            props = torch.cuda.get_device_properties(i)
            total_vram = props.total_memory / (1024**3)
            print(f"   [{i}] {name}")
            print(f"      VRAM Total: {total_vram:.1f}GB")
            print(f"      VRAM Used : {mem_allocated:.1f}GB (Reserved: {mem_reserved:.1f}GB)")
    else:
        print("   Không tìm thấy GPU hoặc CUDA không có sẵn!")

    print("====================================")

if __name__ == "__main__":
    main()
