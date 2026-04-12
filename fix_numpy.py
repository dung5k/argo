import subprocess
import sys

print("Fixing environment...")
try:
    python_exe = sys.executable
    r = subprocess.run([python_exe, "-m", "pip", "install", "numpy<2.0.0", "pandas<2.2.0"], capture_output=True, text=True)
    print("PIP OUTPUT:")
    print(r.stdout[:2000])
    if r.stderr:
        print("PIP ERROR:")
        print(r.stderr[:2000])
        
    import numpy as np
    import torch
    print("NumPy and PyTorch imported successfully!")
    print("NumPy version:", np.__version__)
    print("PyTorch version:", torch.__version__)
    print("CUDA:", torch.cuda.is_available())
except Exception as e:
    import traceback
    traceback.print_exc()
