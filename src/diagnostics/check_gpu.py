import torch
import sys
import subprocess
try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil"])
    import psutil

print("="*40)
print("🔍 BÁO CÁO HỆ THỐNG PHẦN CỨNG CLIENT")
print("="*40)

print(f"🐍 Python Version: {sys.version.split()[0]}")

# RAM Check
ram = psutil.virtual_memory()
print(f"🧠 RAM Tổng: {ram.total / (1024**3):.1f} GB")
print(f"🧠 RAM Khả dụng: {ram.available / (1024**3):.1f} GB ({ram.percent}% sử dụng)")

# CPU Check
cpu_freq = psutil.cpu_freq()
print(f"⚙️ CPU Core: {psutil.cpu_count(logical=False)} Cores / {psutil.cpu_count(logical=True)} Threads")
if cpu_freq:
    print(f"⚙️ CPU Mức Xung: {cpu_freq.current:.0f} Mhz")

# GPU Check
print("\n🎮 [GPU STATUS]")
try:
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        print(f"✅ Phát hiện {gpu_count} GPU hổ trợ CUDA!")
        for i in range(gpu_count):
            print(f"  - Thiết bị {i}: {torch.cuda.get_device_name(i)}")
            print(f"  - Bộ nhớ VRAM: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.1f} GB")
    else:
        print("❌ Không tìm thấy GPU NVIDIA hoặc CUDA chưa được cài đặt. Đang chạy bằng sức mạnh CPU thô sơ!")
except Exception as e:
    print(f"⚠️ Lỗi khi kiểm tra GPU: {e}")

print("="*40)
