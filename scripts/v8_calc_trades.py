import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import pandas as pd
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

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
model.eval()

data_path = "data/v8_test_2026.parquet"
full_df = pd.read_parquet(data_path)
full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()

# Number of trading days
start_dt = full_df.index.min()
end_dt = full_df.index.max()
delta_days = (end_dt - start_dt).days
if delta_days == 0: delta_days = 1

if 'tick_volume' in full_df.columns and 'volume' not in full_df.columns:
    full_df = full_df.rename(columns={'tick_volume': 'volume'})
h1 = full_df.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
h4 = full_df.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
dataset = V8DatasetBuilder(config, full_df, h1, h4)
loader = DataLoader(dataset, batch_size=2048, shuffle=False)

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
max_hold = 12
cooldown = 4

valid_df = dataset.valid_df
n_samples = len(valid_df)

signal_mask_sim = max_trade_probs >= threshold_sim

total_trades = 0
next_allowed = 0

for idx in range(n_samples):
    if idx < next_allowed: continue
    if not signal_mask_sim[idx]: continue
    if idx + max_hold >= n_samples: continue
        
    entry_time = valid_df.index[idx]
    # Chỉ cho phép vào lệnh trước khi đóng NY 1 tiếng (8:00 - 21:59)
    if entry_time.hour >= 22 or entry_time.hour < 8:
        continue
        
    close_candle = idx + max_hold
    total_trades += 1
    row = valid_df.iloc[idx]
    direction = trade_dirs[idx].item()
    entry_price = row['close']
    atr_val = row.get('atr', 1.5)
    tp_dist = atr_val * 3.0
    sl_dist = atr_val * 1.5
    if direction == 1:
        tp_price = entry_price + tp_dist
        sl_price = entry_price - sl_dist
    else:
        tp_price = entry_price - tp_dist
        sl_price = entry_price + sl_dist
        
    result = 'scratch'
    for k in range(1, max_hold + 1):
        fi = idx + k
        if fi >= n_samples:
            break
        check_time = valid_df.index[fi]
        # Đóng lệnh cưỡng bức khi kết thúc phiên NY (23:00)
        if check_time.hour >= 23 or check_time.hour < 8:
            result = 'scratch'
            close_candle = fi
            break
            
        fh = valid_df.iloc[fi]['high']
        fl = valid_df.iloc[fi]['low']
        if direction == 1:
            if fl <= sl_price: result = 'loss'; close_candle = fi; break
            if fh >= tp_price: result = 'win'; close_candle = fi; break
        else:
            if fh >= sl_price: result = 'loss'; close_candle = fi; break
            if fl <= tp_price: result = 'win'; close_candle = fi; break
            
    next_allowed = close_candle + cooldown

trades_per_day = total_trades / delta_days

print("="*50)
print(f"Total Days: {delta_days}")
print(f"Total Trades: {total_trades}")
print(f"Trades per Day: {trades_per_day:.2f}")
print("="*50)
