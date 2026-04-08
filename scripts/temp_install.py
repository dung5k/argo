import subprocess
import sys

print("[ENV_FIX] Installing requests and huggingface_hub...")
subprocess.run([sys.executable, "-m", "pip", "install", "requests", "huggingface_hub"])
print("[ENV_FIX] Installed.")
