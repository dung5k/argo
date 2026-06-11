import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

print("=== FINETUNING OPT-1 (2026 Jan-Apr) & TESTING (May-Present) ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Loading 2026 data...")
data_path = "data/v8_test_2026.parquet"
full_df = pd.read_parquet(data_path)
full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()

# Split train and test
train_df = full_df.loc[:'2026-04-30 23:59:59']
test_df = full_df.loc['2026-05-01 00:00:00':]

print(f"Train samples: {len(train_df)}")
print(f"Test samples:  {len(test_df)}")

print("\nBuilding Train Dataset (takes a few mins)...")
train_h1 = train_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
train_h4 = train_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
train_dataset = V8DatasetBuilder(config, train_df, train_h1, train_h4)
train_loader = DataLoader(train_dataset, batch_size=128, shuffle=True, drop_last=True)

print("\nBuilding Test Dataset (takes a few mins)...")
test_h1 = test_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_h4 = test_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_dataset = V8DatasetBuilder(config, test_df, test_h1, test_h4)
test_loader = DataLoader(test_dataset, batch_size=2048, shuffle=False)

# Keep test tensors in memory for fast evaluation
print("\nBuffering test data...")
all_m15, all_h1, all_h4, all_cont, all_y = [], [], [], [], []
for x_m15, x_h1, x_h4, cont_x, y in test_loader:
    all_m15.append(x_m15.to(device))
    all_h1.append(x_h1.to(device))
    all_h4.append(x_h4.to(device))
    all_cont.append(cont_x.to(device))
    all_y.append(y.to(device))

# Load Model
model_name = "brain_OPT-1_S17_PnL+163.pt"
m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{model_name}"
print(f"\nLoading weights from {m_path}")
state_dict = torch.load(m_path, map_location=device, weights_only=False)
layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
num_layers = max(layer_indices) + 1 if layer_indices else 3
config['transformer_params']['num_layers'] = num_layers
model = V8TransformerModel(config)
model.load_state_dict(state_dict)
model.to(device)

# Fine-tuning setup
criterion = nn.CrossEntropyLoss()
# Use small learning rate for fine-tuning
optimizer = optim.AdamW(model.parameters(), lr=1e-5, weight_decay=1e-4)
epochs = 5

print("\nStarting Fine-tuning...")
for ep in range(epochs):
    model.train()
    total_loss = 0
    for x_m15, x_h1, x_h4, cont_x, y in train_loader:
        x_m15, x_h1, x_h4, cont_x, y = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device), y.to(device)
        optimizer.zero_grad()
        out = model(x_m15, x_h1, x_h4, cont_x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    print(f"Epoch {ep+1}/{epochs} - Train Loss: {total_loss/len(train_loader):.4f}")

# Evaluation
print("\nStarting Evaluation on Test Data (May - Present)...")
model.eval()
all_probs = []
with torch.no_grad():
    for i in range(len(all_m15)):
        out = model(all_m15[i], all_h1[i], all_h4[i], all_cont[i])
        probs = torch.softmax(out, dim=1)
        all_probs.append(probs)
        
all_probs = torch.cat(all_probs, dim=0)
prob_s2 = all_probs[:, 0]
prob_b2 = all_probs[:, 4]
max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)

threshold_sim = 0.30
spread = 0.3
tp_mult = 3.0
sl_mult = 1.5
max_hold = 12
cooldown = 4
valid_df = test_dataset.valid_df
n_samples = len(valid_df)

signal_mask_sim = max_trade_probs >= threshold_sim

wins = 0
losses = 0
scratches = 0
total_pnl = 0.0
trade_results = []
max_drawdown = 0.0
equity_peak = 0.0
equity = 0.0
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
    
    if direction == 1:  # BUY
        real_entry = entry_price + spread / 2
        tp_price = real_entry + tp_dist
        sl_price = real_entry - sl_dist
    else:  # SELL
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
            if fl <= sl_price:
                result = 'loss'; pnl = -sl_dist; close_candle = fi; break
            if fh >= tp_price:
                result = 'win'; pnl = tp_dist; close_candle = fi; break
        else:
            if fh >= sl_price:
                result = 'loss'; pnl = -sl_dist; close_candle = fi; break
            if fl <= tp_price:
                result = 'win'; pnl = tp_dist; close_candle = fi; break
    
    if result == 'scratch':
        close_price = valid_df.iloc[close_candle]['close']
        if direction == 1: pnl = close_price - real_entry
        else: pnl = real_entry - close_price
        
    next_allowed = close_candle + cooldown
    
    if result == 'win': wins += 1
    elif result == 'loss': losses += 1
    else: scratches += 1
        
    total_pnl += pnl
    equity += pnl
    equity_peak = max(equity_peak, equity)
    current_dd = equity_peak - equity
    max_drawdown = max(max_drawdown, current_dd)
    trade_results.append(pnl)

total_trades = wins + losses + scratches
real_wr = (wins / total_trades * 100) if total_trades > 0 else 0
gross_win = sum(p for p in trade_results if p > 0)
gross_loss = abs(sum(p for p in trade_results if p < 0))
pf = (gross_win / gross_loss) if gross_loss > 0 else 999.0

print("\n" + "="*75)
print(f"Fine-tuned {model_name} on 2026 Jan-Apr. Tested on May-Jun.")
print(f"PnL: {total_pnl:+.1f} | PF: {pf:.2f} | WR: {real_wr:.1f}% | DD: {max_drawdown:.1f} | Trades: {total_trades}")
print("="*75)

import datetime
ts = datetime.datetime.now().strftime("%y%m%d_%H%M")
out_name = f"v8_configs/hall_of_fame/brain_OPT-1_S17_FINETUNED_PnL{total_pnl:+.0f}_{ts}.pt"
torch.save(model.state_dict(), out_name)
print(f"Saved to: {out_name}")
