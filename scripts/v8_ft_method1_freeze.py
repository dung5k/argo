import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader
import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

print("=== METHOD 1: FREEZE DEEP LAYERS ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model_name = "brain_OPT-12_EWC_PnL+44.pt"
m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{model_name}"
state_dict = torch.load(m_path, map_location=device, weights_only=False)
layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
num_layers = max(layer_indices) + 1 if layer_indices else 3
config['transformer_params']['num_layers'] = num_layers
model = V8TransformerModel(config)
model.load_state_dict(state_dict)
model.to(device)

# FREEZE LAYERS 0 to num_layers-3 (Keep last 2 layers and FC)
print(f"Freezing embedding and first {num_layers-2} layers...")
for name, param in model.named_parameters():
    if "embedding" in name or "pos_encoder" in name:
        param.requires_grad = False
    elif "transformer_encoder.layers" in name:
        layer_idx = int(name.split('.')[2])
        if layer_idx < num_layers - 2:
            param.requires_grad = False

class_weights = torch.tensor([1.0/0.15, 1.0/0.10, 1.0/0.50, 1.0/0.10, 1.0/0.15]).to(device)
class_weights = class_weights / class_weights.sum() * 5.0
criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)

# Step 2: Load 2026 data
print("Loading 2026 data...")
data_path = "data/v8_test_2026.parquet"
full_df = pd.read_parquet(data_path)
full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()

train_df = full_df.loc[:'2026-04-30 23:59:59']
test_df = full_df.loc['2026-05-01 00:00:00':]

new_h1 = train_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
new_h4 = train_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
new_dataset = V8DatasetBuilder(config, train_df, new_h1, new_h4)
new_loader = DataLoader(new_dataset, batch_size=128, shuffle=True)

test_h1 = test_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_h4 = test_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_dataset = V8DatasetBuilder(config, test_df, test_h1, test_h4)
test_loader = DataLoader(test_dataset, batch_size=2048, shuffle=False)

optimizer = optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-5, weight_decay=1e-4)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)

print("\nStarting Finetuning with Frozen Layers...")
epochs = 5
best_loss = float('inf')
best_model_state = None

threshold_sim = 0.30
spread = 0.3
tp_mult = 3.0
sl_mult = 1.5
max_hold = 12
cooldown = 4

for epoch in range(epochs):
    model.train()
    total_loss = 0
    for x_m15, x_h1, x_h4, cont_x, y in new_loader:
        x_m15, x_h1, x_h4, cont_x, y = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device), y.to(device)
        optimizer.zero_grad()
        out = model(x_m15, x_h1, x_h4, cont_x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
        
    model.eval()
    val_loss = 0
    all_probs = []
    with torch.no_grad():
        for x_m15, x_h1, x_h4, cont_x, y in test_loader:
            x_m15, x_h1, x_h4, cont_x, y = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device), y.to(device)
            out = model(x_m15, x_h1, x_h4, cont_x)
            v_loss = criterion(out, y)
            val_loss += v_loss.item()
            probs = torch.softmax(out, dim=1)
            all_probs.append(probs)
            
    all_probs = torch.cat(all_probs, dim=0)
    prob_s2 = all_probs[:, 0]
    prob_b2 = all_probs[:, 4]
    max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)
    signal_mask_sim = max_trade_probs >= threshold_sim
    
    valid_df = test_dataset.valid_df
    n_samples = len(valid_df)
    wins, losses, scratches, total_pnl = 0, 0, 0, 0.0
    next_allowed = 0
    
    for idx in range(n_samples):
        if idx < next_allowed: continue
        if not signal_mask_sim[idx]: continue
        if idx + max_hold >= n_samples: continue
            
        row = valid_df.iloc[idx]
        entry_price = row['close']
        atr_val = row.get('atr', 1.5)
        if atr_val <= 0 or pd.isna(atr_val): atr_val = 1.5
        direction = trade_dirs[idx].item()
        tp_dist = atr_val * tp_mult
        sl_dist = atr_val * sl_mult
        
        if direction == 1:
            real_entry = entry_price + spread / 2
            tp_price = real_entry + tp_dist
            sl_price = real_entry - sl_dist
        else:
            real_entry = entry_price - spread / 2
            tp_price = real_entry - tp_dist
            sl_price = real_entry + sl_dist
        
        result = 'scratch'
        pnl = 0.0
        close_candle = idx + max_hold
        
        for k in range(1, max_hold + 1):
            fi = idx + k
            fh = valid_df.iloc[fi]['high']
            fl = valid_df.iloc[fi]['low']
            if direction == 1:
                if fl <= sl_price: result = 'loss'; pnl = -sl_dist; close_candle = fi; break
                if fh >= tp_price: result = 'win'; pnl = tp_dist; close_candle = fi; break
            else:
                if fh >= sl_price: result = 'loss'; pnl = -sl_dist; close_candle = fi; break
                if fl <= tp_price: result = 'win'; pnl = tp_dist; close_candle = fi; break
        
        if result == 'scratch':
            close_price = valid_df.iloc[close_candle]['close']
            if direction == 1: pnl = close_price - real_entry
            else: pnl = real_entry - close_price
            
        next_allowed = close_candle + cooldown
        if result == 'win': wins += 1
        elif result == 'loss': losses += 1
        else: scratches += 1
        total_pnl += pnl
        
    train_ce = total_loss/len(new_loader)
    val_avg = val_loss/len(test_loader)
    total_trades = wins + losses + scratches
    real_wr = (wins / total_trades * 100) if total_trades > 0 else 0
    print(f"Ep {epoch+1} | CE: {train_ce:.3f} | Val Loss: {val_avg:.3f} | PnL: {total_pnl:+.1f} | Trades: {total_trades} | WR: {real_wr:.1f}%")
    
    scheduler.step(val_avg)
    if val_avg < best_loss:
        best_loss = val_avg
        best_model_state = model.state_dict().copy()

print(f"\nTraining Complete. Loading best model (Loss: {best_loss:.3f}).")
model.load_state_dict(best_model_state)

base_mname = model_name.replace(".pt", "")
ts = datetime.datetime.now().strftime("%y%m%d_%H%M")
out_name = f"v8_configs/hall_of_fame/{base_mname}_FTM1_PnL{total_pnl:+.0f}_{ts}.pt"
torch.save(model.state_dict(), out_name)
print(f"Saved: {out_name}")
print("M1_DONE")
