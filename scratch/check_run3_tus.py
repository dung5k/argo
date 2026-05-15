import os
import sys
import json
import torch
import numpy as np
from torch.utils.data import TensorDataset, DataLoader

sys.path.insert(0, r"d:\DungLA\client1")
from src.training_v6.model_v6 import AAMT_MTF_Model
from src.training_v3.evaluator_v3 import WinRateEvaluatorV3

run_dir = r"d:\DungLA\client1\workspaces\CFG_LTC_ASIAN_V6\runs\run_20260510_134031_v6_asian_auto_3"
config_path = os.path.join(run_dir, "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

tensor_dir = os.path.join(run_dir, "data", "tensors")
import glob
cfg_id = config.get("CONFIG_ID", "CFG_LTC_ASIAN_V6")
x_files = sorted(glob.glob(os.path.join(tensor_dir, f"X_tensor_{cfg_id}_tf*.npy")))
x_tensors = [np.load(f) for f in x_files]
y_path = os.path.join(tensor_dir, f"Y_tensor_{cfg_id}.npy")
y_tensor = np.load(y_path)

train_size = int(0.8 * len(y_tensor))
val_x = [torch.tensor(t[train_size:], dtype=torch.float32) for t in x_tensors]
val_y = torch.tensor(y_tensor[train_size:], dtype=torch.long)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

train_cfg = config.get("TRAINING", {})
d_model = train_cfg.get("D_MODEL", 128)
nheads = train_cfg.get("N_HEADS", train_cfg.get("N_HEAD", 8))
num_layers = train_cfg.get("NUM_LAYERS", 4)
dropout = train_cfg.get("DROPOUT", 0.25)
d_ff = train_cfg.get("D_FF", 512)
pooling = train_cfg.get("POOLING", "mean")
cls_head = train_cfg.get("CLS_HEAD", "simple")
layer_drop = train_cfg.get("LAYER_DROP", 0.0)

input_dims = [X.shape[2] for X in val_x]
seq_lens = [X.shape[1] for X in val_x]

model = AAMT_MTF_Model(
    input_dims=input_dims, 
    seq_lens=seq_lens,
    d_model=d_model,
    nhead=nheads,
    num_layers=num_layers,
    dropout=dropout,
    d_ff=d_ff,
    pooling=pooling,
    cls_head=cls_head,
    layer_drop=layer_drop
).to(device)

model.load_state_dict(torch.load(os.path.join(run_dir, "brains", "aamt_v3_CFG_LTC_ASIAN_V6_final.pth"), map_location=device))
model.eval()

all_logits = []
val_dataset = TensorDataset(*val_x, val_y)
val_loader = DataLoader(val_dataset, batch_size=256, shuffle=False)

with torch.no_grad():
    for batch in val_loader:
        inputs = [x.to(device) for x in batch[:-1]]
        _, logits, _ = model(inputs)
        all_logits.append(logits.cpu())

cat_logits = torch.cat(all_logits, dim=0)

probs = torch.softmax(cat_logits, dim=1)
prob_sell = probs[:, 0]
prob_buy = probs[:, 1]

thresholds = [0.53, 0.6167, 0.7033, 0.79]

for t in thresholds:
    buy_mask = prob_buy > t
    sell_mask = prob_sell > t
    signals = (buy_mask | sell_mask).float()
    total_signals = int(signals.sum().item())
    
    chunk_size = 400
    N = len(signals)
    chunks = [int(signals[i:i+chunk_size].sum().item()) for i in range(0, N, chunk_size)]
    active_chunks = [c for c in chunks if c > 0]
    
    tus = WinRateEvaluatorV3.calculate_distribution_penalty(buy_mask, sell_mask, chunk_size=400)
    
    print(f"\n========================================================")
    print(f"Threshold: >= {t*100:.0f}%")
    print(f"Total Signals: {total_signals}")
    print(f"Active Days: {len(active_chunks)} / {max(1, len(chunks))} ({len(active_chunks)/max(1, len(chunks))*100:.1f}%)")
    print(f"TUS (Trade Uniformity Score): {tus:.4f}")
    
    chunks_indexed = [(i, c) for i, c in enumerate(chunks)]
    chunks_indexed.sort(key=lambda x: x[1], reverse=True)
    print(f"Phân bổ 10 ngày nhộn nhịp nhất:")
    for idx, c in chunks_indexed[:10]:
        if c > 0:
            print(f"  Day {idx+1}: {c} lệnh")
