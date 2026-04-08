import sys, os, torch, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor')

try:
    from src.legacy.train_ga import TransformerModel
except:
    from legacy.train_ga import TransformerModel

import glob

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_weights = sorted(glob.glob(os.path.join(runs_dir, '**', 'xauusd_unified_weights_BEST_VLOSS.pth'), recursive=True))
print(f"XAU weight files: {[os.path.basename(os.path.dirname(f)) for f in xau_weights]}")

if xau_weights:
    latest = xau_weights[-1]
    state = torch.load(latest, map_location='cpu', weights_only=True)
    
    # Check proj layers 
    for key in state.keys():
        if 'weight' in key:
            print(f"  {key}: {state[key].shape}")

    for n in [86, 87, 100, 101]:
        for xau_n in [8, 18]:
            try:
                model = TransformerModel(num_features=n, d_model=256, nhead=8, num_layers=3, 
                                          dropout_rate=0.2, num_xau_features=xau_n)
                model.load_state_dict(state)
                print(f"SUCCESS: num_features={n}, num_xau_features={xau_n}")
            except Exception as e:
                pass  # quietly fail, just print successes
