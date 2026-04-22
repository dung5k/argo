import subprocess
import sys

print("[FIX] Bắt đầu gỡ cài đặt Numpy cũ và cài lại Numpy 1.x...")
try:
    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "numpy"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy<2.0.0"])
    
    # Kiểm tra lại version
    result = subprocess.run([sys.executable, "-c", "import numpy; print(numpy.__version__)"], capture_output=True, text=True)
    print(f"[FIX] Numpy đã khôi phục về phiên bản: {result.stdout.strip()}")
except Exception as e:
    print(f"[FIX] Lỗi khi xử lý Numpy: {e}")
