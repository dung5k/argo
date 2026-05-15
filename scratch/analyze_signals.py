import os
import sys
import json
import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
import datetime

sys.path.insert(0, r'd:\DungLA\client1')
from src.training_v6.model_v6 import AAMT_MTF_Model

cfg_id = 'CFG_LTC_WEEKEND_V6'
run_id = 'run_20260509_162500_v6_weekend_tuning_28'
run_dir = f'workspaces/{cfg_id}/runs/{run_id}'

# Load config
with open(f'{run_dir}/config.json', 'r') as f:
    config = json.load(f)

# Load Data
X0 = np.load(f'{run_dir}/data/tensors/X_tensor_{cfg_id}_tf0.npy')
X1 = np.load(f'{run_dir}/data/tensors/X_tensor_{cfg_id}_tf1.npy')
X2 = np.load(f'{run_dir}/data/tensors/X_tensor_{cfg_id}_tf2.npy')
Y  = np.load(f'{run_dir}/data/tensors/Y_tensor_{cfg_id}.npy')

# Split 80/20
val_idx = int(len(Y) * 0.8)
gap = 2880
val_start = val_idx + gap
if val_start >= len(Y):
    val_start = val_idx

X0_val = X0[val_start:]
X1_val = X1[val_start:]
X2_val = X2[val_start:]
Y_val = Y[val_start:]

print(f"Validation shape: {len(Y_val)}")

# Model config
train_cfg = config.get("TRAINING", {})
d_model = train_cfg.get("D_MODEL", 128)
nhead = train_cfg.get("N_HEAD", 8)
num_layers = train_cfg.get("NUM_LAYERS", 4)
# In train_v6.py, d_ff is hardcoded to 512
d_ff = 512

mtf_inputs = config["FEATURE_ENGINEERING"]["MTF_INPUTS"]
input_dims = [len(tf.get("FEATURES", [])) for tf in mtf_inputs]
seq_lens = [tf.get("WINDOW_SIZE", 60) for tf in mtf_inputs]

model = AAMT_MTF_Model(
    input_dims=input_dims,
    seq_lens=seq_lens,
    d_model=d_model,
    nhead=nhead,
    num_layers=num_layers,
    dropout=0.0,
    num_classes=3,
    d_ff=d_ff,
    pooling='mean',
    cls_head='simple',
    layer_drop=0.0
)

# Load weights
weights_path = f"{run_dir}/brains/aamt_v3_{cfg_id}_final.pth"
state_dict = torch.load(weights_path, map_location='cpu')
model.load_state_dict(state_dict)
model.eval()

device = torch.device('cpu')
model.to(device)

all_probs = []
batch_size = 512
with torch.no_grad():
    for i in range(0, len(X0_val), batch_size):
        b_x0 = torch.FloatTensor(X0_val[i:i+batch_size]).to(device)
        b_x1 = torch.FloatTensor(X1_val[i:i+batch_size]).to(device)
        b_x2 = torch.FloatTensor(X2_val[i:i+batch_size]).to(device)
        _, logits, _ = model([b_x0, b_x1, b_x2])
        probs = F.softmax(logits, dim=-1).cpu().numpy()
        all_probs.extend(probs)

all_probs = np.array(all_probs)

# Analyze
print("Mean Probs [Sell, Hold, Buy]:", all_probs.mean(axis=0))
print("Max Probs [Sell, Hold, Buy]:", all_probs.max(axis=0))

for thr in [0.45, 0.50, 0.53, 0.55, 0.60, 0.65]:
    buys = np.sum(all_probs[:, 2] >= thr)
    sells = np.sum(all_probs[:, 0] >= thr)
    print(f"Threshold {thr:.2f} -> Buys: {buys}, Sells: {sells}")

# Find cluster for > 0.45
buy_idx = np.where(all_probs[:, 2] >= 0.45)[0]
sell_idx = np.where(all_probs[:, 0] >= 0.45)[0]

print("Buy Indices (>0.45):", buy_idx)
print("Sell Indices (>0.45):", sell_idx)

# Density checking
if len(buy_idx) > 0:
    print(f"Buy clusters (diffs):", np.diff(buy_idx))
