import sys
try:
    import torch
    print("Torch loaded successfully!")
    print(torch.__version__)
    print(f"CUDA Available: {torch.cuda.is_available()}")
except Exception as e:
    import traceback
    print("Failed to load torch:")
    traceback.print_exc()
