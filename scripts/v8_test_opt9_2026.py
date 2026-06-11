import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import torch.nn as nn
import pandas as pd
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

print("=== TESTING OPT-9 S15 ON 2026 DATA ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

model_name = "brain_OPT-9_S15_PnL+257.pt"
m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{model_name}"
print(f"Loading weights from {m_path}")
state_dict = torch.load(m_path, map_location=device, weights_only=False)
layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
num_layers = max(layer_indices) + 1 if layer_indices else 3
config['transformer_params']['num_layers'] = num_layers
model = V8TransformerModel(config)
model.load_state_dict(state_dict)
model.to(device)

print("\nLoading 2026 data...")
data_path = "data/v8_test_2026.parquet"
full_df = pd.read_parquet(data_path)
full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()

print("Building Dataset...")
h1 = full_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
h4 = full_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
dataset = V8DatasetBuilder(config, full_df, h1, h4)
loader = DataLoader(dataset, batch_size=2048, shuffle=False)

print("\nStarting Evaluation on 2026 Data...")
model.eval()
all_probs = []
with torch.no_grad():
    for x_m15, x_h1, x_h4, cont_x, y in loader:
        x_m15, x_h1, x_h4, cont_x = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device)
        out = model(x_m15, x_h1, x_h4, cont_x)
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

valid_df = dataset.valid_df
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

print("\n" + "="*75)
print(f"Tested {model_name} on ENTIRE 2026 DATA.")
print(f"PnL: {total_pnl:+.1f} | WR: {real_wr:.1f}% | DD: {max_drawdown:.1f} | Trades: {total_trades}")
print(f"Wins: {wins} | Losses: {losses} | Scratches: {scratches}")
print("="*75)
