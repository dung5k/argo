import os
import sys
import torch
import numpy as np
import json

# Setup paths
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.training_v3.model_v3 import AAMT_Model

def evaluate_on_val_set():
    run_id = "run_20260504_192200_v4_hour_lookback"
    workspace = "workspaces/CFG_LTC_ASIAN_V3_5"
    run_dir = os.path.join(workspace, "runs", run_id)
    results_dir = os.path.join(run_dir, "results")
    
    with open(os.path.join(results_dir, "config.json"), 'r') as f:
        config = json.load(f)
    
    # Load Model
    model_path = os.path.join(run_dir, "brains", f"aamt_v3_{config['CONFIG_ID']}_final.pth")
    checkpoint = torch.load(model_path, map_location='cpu')
    state_dict = checkpoint.get('model_state_dict', checkpoint)
    
    input_dim = state_dict['encoder.input_projection.weight'].shape[1]
    model = AAMT_Model(
        input_dim=input_dim,
        d_model=config['TRAINING'].get('D_MODEL', 128),
        nhead=config['TRAINING'].get('N_HEAD', 8),
        num_layers=config['TRAINING'].get('NUM_LAYERS', 4),
        pooling=checkpoint.get('pooling', config['TRAINING'].get('POOLING', 'mean')),
        cls_head=checkpoint.get('cls_head', config['TRAINING'].get('CLS_HEAD', 'simple'))
    )
    model.load_state_dict(state_dict)
    model.eval()
    
    # Load Tensors
    tensor_dir = os.path.join(run_dir, "data", "tensors")
    X = np.load(os.path.join(tensor_dir, f"X_tensor_{config['CONFIG_ID']}.npy"))
    Y = np.load(os.path.join(tensor_dir, f"Y_tensor_{config['CONFIG_ID']}.npy"))
    
    # Take last 20% (Validation set)
    val_size = int(len(X) * 0.2)
    X_val = X[-val_size:]
    Y_val = Y[-val_size:]
    
    X_tensor = torch.tensor(X_val).float()
    Y_tensor = torch.tensor(Y_val).long()
    
    with torch.no_grad():
        _, logits, _ = model(X_tensor)
        probs = torch.softmax(logits, dim=1)
        
    thresholds = [0.53, 0.55, 0.57, 0.60]
    print("\n--- VALIDATION SET PERFORMANCE (from Training Data) ---")
    for t in thresholds:
        buy_mask = probs[:, 1] > t
        sell_mask = probs[:, 0] > t
        n_buy, n_sell = buy_mask.sum().item(), sell_mask.sum().item()
        n_total = n_buy + n_sell
        if n_total == 0: continue
        correct_buy = (Y_tensor[buy_mask] == 1).sum().item()
        correct_sell = (Y_tensor[sell_mask] == 0).sum().item()
        wr = (correct_buy + correct_sell) / n_total
        print(f"Threshold {t*100:.1f}%: WR={wr*100:.2f}% | Total={n_total} (Buy={n_buy}, Sell={n_sell})")

if __name__ == "__main__":
    evaluate_on_val_set()
