"""
Read model state dict shapes to understand expected input size
"""
import sys, os, torch
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor')

import glob

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_weights = sorted(glob.glob(os.path.join(runs_dir, '**', 'xauusd_unified_weights_BEST_VLOSS.pth'), recursive=True))

print(f"XAU weight files: {[os.path.basename(os.path.dirname(f)) for f in xau_weights]}")

if xau_weights:
    latest = xau_weights[-1]
    print(f"\nInspecting: {latest}")
    
    state = torch.load(latest, map_location='cpu', weights_only=True)
    
    print("\nAll layers with shapes:")
    for key, val in state.items():
        print(f"  {key}: {val.shape}")
