import sys, os, torch, json
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor')

try:
    from src.legacy.train_ga import TransformerModel
except:
    from legacy.train_ga import TransformerModel

import glob

runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'
xau_weights = sorted(glob.glob(os.path.join(runs_dir, '**', 'xauusd_unified_weights_BEST_VLOSS.pth'), recursive=True))
with open('model_test_results.txt', 'w') as out:
    out.write(f"XAU weight files: {[os.path.basename(os.path.dirname(f)) for f in xau_weights]}\n")

    if xau_weights:
        latest = xau_weights[-1]
        out.write(f"Testing: {latest}\n")
        state = torch.load(latest, map_location='cpu', weights_only=True)
        
        for key in state.keys():
            if 'weight' in key:
                out.write(f"  {key}: {state[key].shape}\n")

        for n in [86, 87, 100, 101]:
            for xau_n in [8, 18]:
                try:
                    model = TransformerModel(num_features=n, d_model=256, nhead=8, num_layers=3, 
                                              dropout_rate=0.2, num_xau_features=xau_n)
                    model.load_state_dict(state)
                    out.write(f"SUCCESS: num_features={n}, num_xau_features={xau_n}\n")
                    
                    # test inference
                    test = torch.zeros(1, 60, n)
                    with torch.no_grad():
                        result = model(test)
                    out.write(f"  Inference output: {result.shape}\n")
                except Exception as e:
                    out.write(f"FAILED {n}+{xau_n}: {str(e)[:100]}\n")
                    
print("Results written to model_test_results.txt")
