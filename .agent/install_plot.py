import subprocess
import sys
# Cài đặt
try:
    print("Installing matplotlib...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib"])
    print("Matplotlib install done!")
except Exception as e:
    print(f"Lỗi: {e}")
