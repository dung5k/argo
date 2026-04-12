import subprocess
import sys
import os

log_file = os.path.join(os.getcwd(), "install_pytorch.log")

script = f"""
import subprocess
import sys

with open(r"{log_file}", "w", encoding="utf-8") as f:
    f.write("Bắt đầu khôi phục PyTorch CPU...\\n")

try:
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"], check=False)
    
    res = subprocess.run([
        sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"
    ], capture_output=True, text=True, encoding="utf-8")
    
    with open(r"{log_file}", "a", encoding="utf-8") as f:
        f.write("\\n--- CÀI ĐẶT ---\\n")
        f.write(res.stdout)
        if res.stderr:
            f.write("\\n--- LỖI (NẾU CÓ) ---\\n")
            f.write(res.stderr)
        f.write("\\nCài đặt hoàn tất.\\n")
        
except Exception as e:
    with open(r"{log_file}", "a", encoding="utf-8") as f:
        f.write(f"\\n[NGOẠI LỆ]: {{e}}\\n")
"""

temp_installer = os.path.join(os.getcwd(), "temp_pip_installer_cpu.py")
with open(temp_installer, "w", encoding="utf-8") as f:
    f.write(script)

# Run detached
DETACHED_PROCESS = 0x00000008
subprocess.Popen([sys.executable, temp_installer], creationflags=DETACHED_PROCESS)

print(f"[CLIENT][INSTALL] Đã khởi động cài đặt KHÔI PHỤC BẢN CPU. File log: {log_file}")
