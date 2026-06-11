import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
from torch.utils.data import DataLoader

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

print("=== DIRECTION 1: WALK-FORWARD EXTENSION ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Load model S17
model_name = "brain_OPT-1_S17_PnL+163.pt"
m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{model_name}"
print(f"Loading weights from {m_path}")
state_dict = torch.load(m_path, map_location=device, weights_only=False)
layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
num_layers = max(layer_indices) + 1 if layer_indices else 3
config['transformer_params']['num_layers'] = num_layers
model = V8TransformerModel(config)
model.load_state_dict(state_dict)
model.to(device)

class_weights = torch.tensor([1.0/0.15, 1.0/0.10, 1.0/0.50, 1.0/0.10, 1.0/0.15]).to(device)
class_weights = class_weights / class_weights.sum() * 5.0
criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)

# Training on Split 18, 19, 20
splits = [18, 19, 20]
batch_size = 128
base_lr = 1e-4 # Same as original training

threshold_sim = 0.30
spread = 0.3
tp_mult = 3.0
sl_mult = 1.5
max_hold = 12
cooldown = 4

for split_id in splits:
    print(f"\n--- Processing Split {split_id} ---")
    train_file = f"data/v8_splits/split_{split_id}_train.parquet"
    test_file = f"data/v8_splits/split_{split_id}_test.parquet"
    
    df_train = pd.read_parquet(train_file)
    train_h1 = df_train.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    train_h4 = df_train.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    train_dataset = V8DatasetBuilder(config, df_train, train_h1, train_h4)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    df_test = pd.read_parquet(test_file)
    test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    test_dataset = V8DatasetBuilder(config, df_test, test_h1, test_h4)
    test_loader = DataLoader(test_dataset, batch_size=2048, shuffle=False)
    
    optimizer = optim.AdamW(model.parameters(), lr=base_lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)
    
    best_loss = float('inf')
    best_model_state = None
    
    epochs = 5
    for epoch in range(epochs):
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
            
        train_avg = total_loss/len(train_loader)
        val_avg = val_loss/len(test_loader)
        print(f"Ep {epoch+1} | Loss: {train_avg:.3f}/{val_avg:.3f} | PnL: {total_pnl:+.1f} | W:{wins} L:{losses} S:{scratches}")
        
        scheduler.step(val_avg)
        if val_avg < best_loss:
            best_loss = val_avg
            best_model_state = model.state_dict().copy()
            
    print(f"End of Split {split_id}. Loading best model (Loss: {best_loss:.3f}) for next split.")
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    import datetime
    ts = datetime.datetime.now().strftime("%y%m%d_%H%M")
    out_name = f"v8_configs/hall_of_fame/brain_OPT-1_WF_S{split_id}_PnL{total_pnl:+.0f}_{ts}.pt"
    torch.save(model.state_dict(), out_name)
    print(f"Saved: {out_name}")

print("=== WALK-FORWARD COMPLETD ===")
