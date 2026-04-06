"""
Check model input size vs tensor we're feeding
"""
import sys, os, torch, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\src')
sys.path.insert(0, r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor')

# Load model
try:
    from src.legacy.train_ga import TransformerModel
except:
    from legacy.train_ga import TransformerModel

import glob

data_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data'
runs_dir = r'C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\runs'

# Find latest XAU model
xau_weights = sorted(glob.glob(os.path.join(runs_dir, '**', 'xauusd_unified_weights_BEST_VLOSS.pth'), recursive=True))
print(f"XAU weight files: {[os.path.basename(os.path.dirname(f)) for f in xau_weights]}")

if not xau_weights:
    print("No XAU weights found locally")
else:
    latest = xau_weights[-1]
    print(f"Using: {latest}")
    
    # Load state dict to inspect shapes
    state = torch.load(latest, map_location='cpu', weights_only=True)
    print("\nModel state dict keys (first 5):", list(state.keys())[:5])
    
    # Check first layer to determine input size
    # Usually embedding.weight or input_proj.weight
    for key in state.keys():
        if 'weight' in key and len(state[key].shape) == 2:
            print(f"  {key}: {state[key].shape}")
            if state[key].shape[1] > 1:  # input layer
                print(f"    => This is likely an input layer accepting {state[key].shape[1]} features")
                break
    
    # Try loading model with num_features=86 (as training_metrix says)
    print("\nTrying to load with num_features=86, num_xau_features=18...")
    try:
        model = TransformerModel(num_features=86, d_model=256, nhead=8, num_layers=3, 
                                  dropout_rate=0.2, num_xau_features=18)
        model.load_state_dict(state)
        print("SUCCESS: model loaded with 86 features!")
        
        # Test inference
        test_tensor = torch.zeros(1, 60, 86)
        with torch.no_grad():
            out = model(test_tensor)
        print(f"Inference output shape: {out.shape}")
        print("Model expects: 86 features per timestep")
        
    except Exception as e:
        print(f"FAILED with 86: {e}")
        
    print("\nTrying to load with num_features=100...")
    try:
        model2 = TransformerModel(num_features=100, d_model=256, nhead=8, num_layers=3, 
                                  dropout_rate=0.2, num_xau_features=18)
        model2.load_state_dict(state)
        print("SUCCESS: model loaded with 100 features!")
    except Exception as e:
        print(f"FAILED with 100: {e}")
        
    print("\nTrying to load with num_features=101...")
    try:
        model3 = TransformerModel(num_features=101, d_model=256, nhead=8, num_layers=3, 
                                  dropout_rate=0.2, num_xau_features=18)
        model3.load_state_dict(state)
        print("SUCCESS: model loaded with 101 features!")
    except Exception as e:
        print(f"FAILED with 101: {e}")
