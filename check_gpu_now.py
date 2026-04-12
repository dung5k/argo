import torch
import subprocess
try:
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"Device count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device Name: {torch.cuda.get_device_name(0)}")
        
    smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
    if smi.returncode == 0:
        print("\n--- NVIDIA-SMI STATUS ---")
        lines = smi.stdout.split('\n')
        for line in lines[:15]:
            print(line)
        for line in lines[-12:]:
            print(line)
except Exception as e:
    print(f"Error checking GPU: {e}")
