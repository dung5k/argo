import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import torch
import pandas as pd
from torch.utils.data import DataLoader
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

print("=== EVALUATING EWC MODEL ON 2026 DATA (M1 TICK-BY-TICK) ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

if len(sys.argv) > 1:
    model_name = sys.argv[1]
else:
    model_name = "brain_OPT-1_EWC_PnL+48.pt"
m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{model_name}"
print(f"Loading weights from {m_path}")
state_dict = torch.load(m_path, map_location=device, weights_only=False)
layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
num_layers = max(layer_indices) + 1 if layer_indices else 3
config['transformer_params']['num_layers'] = num_layers
model = V8TransformerModel(config)
model.load_state_dict(state_dict)
model.to(device)
model.eval()

threshold_sim = 0.30
spread = 0.3
tp_mult = 3.0
sl_mult = 1.5
max_hold = 12
cooldown = 4

# Load M1 Data for tick-by-tick eval
print("Loading M1 Tick Data...")
df_m1 = pd.read_parquet("data/XAUUSDm_M1_2024_2026.parquet")
print("M1 Data loaded.")

test_file = "data/v8_test_2026.parquet"

df_test = pd.read_parquet(test_file)
if 'tick_volume' in df_test.columns and 'volume' not in df_test.columns:
    df_test = df_test.rename(columns={'tick_volume': 'volume'})
test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
test_dataset = V8DatasetBuilder(config, df_test, test_h1, test_h4)
test_loader = DataLoader(test_dataset, batch_size=2048, shuffle=False)

all_probs = []
with torch.no_grad():
    for x_m15, x_h1, x_h4, cont_x, y in test_loader:
        x_m15, x_h1, x_h4, cont_x = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device)
        out = model(x_m15, x_h1, x_h4, cont_x)
        probs = torch.softmax(out, dim=1)
        all_probs.append(probs)
        
all_probs = torch.cat(all_probs, dim=0)
prob_s2 = all_probs[:, 0]
prob_b2 = all_probs[:, 4]
max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)
signal_mask_sim = max_trade_probs >= threshold_sim

valid_df = test_dataset.valid_df
n_samples = len(valid_df)
wins, losses, scratches = 0, 0, 0
split_pnl = 0.0
next_allowed = 0

running_balance = 0.0
max_balance = 0.0
max_dd = 0.0

print("Evaluating...", end="", flush=True)
for idx in range(n_samples):
    if idx < next_allowed: continue
    if not signal_mask_sim[idx]: continue
    if idx + max_hold >= n_samples: continue
        
    entry_time = valid_df.index[idx] # Time of the M15 candle closing
    # Không vào lệnh trong Phiên Á (23-07) và Đầu Phiên Mỹ (15-18)
    if entry_time.hour >= 23 or entry_time.hour < 8 or (15 <= entry_time.hour <= 18):
        continue
        
    row = valid_df.iloc[idx]
    entry_price = row['close']
    
    atr_val = row.get('atr', 1.5)
    if atr_val <= 0 or pd.isna(atr_val): atr_val = 1.5
    direction = trade_dirs[idx].item()
    tp_dist = atr_val * tp_mult
    sl_dist = atr_val * sl_mult
    
    if direction == 1: # Buy
        real_entry = entry_price + spread / 2
        tp_price = real_entry + tp_dist
        sl_price = real_entry - sl_dist
    else: # Sell
        real_entry = entry_price - spread / 2
        tp_price = real_entry - tp_dist
        sl_price = real_entry + sl_dist
    
    # M1 Evaluation Window (Start at the END of the signal candle)
    start_m1 = entry_time + timedelta(minutes=15)
    end_m1 = start_m1 + timedelta(minutes=max_hold * 15)
    
    # Slice M1 dataframe
    trade_m1 = df_m1.loc[start_m1:end_m1]
    
    result = 'scratch'
    pnl = 0.0
    close_candle = idx + max_hold # default to max hold
    
    if not trade_m1.empty:
        for m1_time, m1_row in trade_m1.iterrows():
            fh = m1_row['high']
            fl = m1_row['low']
            
            # Đóng lệnh cưỡng bức khi kết thúc phiên NY (23:00)
            if m1_time.hour >= 23 or m1_time.hour < 8:
                result = 'scratch'
                minutes_passed = (m1_time - entry_time).total_seconds() / 60
                close_candle = idx + int(minutes_passed // 15)
                break
                
            # Check for hits
            if direction == 1:
                if fl <= sl_price: 
                    result = 'loss'; pnl = -sl_dist; 
                    # approximate close_candle offset
                    minutes_passed = (m1_time - entry_time).total_seconds() / 60
                    close_candle = idx + int(minutes_passed // 15)
                    break
                if fh >= tp_price: 
                    result = 'win'; pnl = tp_dist; 
                    minutes_passed = (m1_time - entry_time).total_seconds() / 60
                    close_candle = idx + int(minutes_passed // 15)
                    break
            else:
                if fh >= sl_price: 
                    result = 'loss'; pnl = -sl_dist; 
                    minutes_passed = (m1_time - entry_time).total_seconds() / 60
                    close_candle = idx + int(minutes_passed // 15)
                    break
                if fl <= tp_price: 
                    result = 'win'; pnl = tp_dist; 
                    minutes_passed = (m1_time - entry_time).total_seconds() / 60
                    close_candle = idx + int(minutes_passed // 15)
                    break
                    
    if result == 'scratch':
        # Kiểm tra đóng lệnh cưỡng bức tại cấp nến M15
        for h_idx in range(idx + 1, close_candle + 1):
            if h_idx >= n_samples:
                break
            check_time = valid_df.index[h_idx]
            if check_time.hour >= 23 or check_time.hour < 8:
                close_candle = h_idx
                break
        close_candle = min(close_candle, n_samples - 1)
        
        # use the last close of the trade_m1, or valid_df close
        if not trade_m1.empty and trade_m1.index[-1].hour < 23:
            close_price = trade_m1.iloc[-1]['close']
        else:
            close_price = valid_df.iloc[close_candle]['close']
            
        if direction == 1: pnl = close_price - real_entry
        else: pnl = real_entry - close_price
        
    next_allowed = min(close_candle + cooldown, n_samples - 1)
    if result == 'win': wins += 1
    elif result == 'loss': losses += 1
    else: scratches += 1
    split_pnl += pnl
    
    running_balance += pnl
    if running_balance > max_balance:
        max_balance = running_balance
    dd = max_balance - running_balance
    if dd > max_dd:
        max_dd = dd
    
total_trades = wins + losses + scratches
real_wr = (wins / total_trades * 100) if total_trades > 0 else 0

print(f"2026 DATA | PnL: {split_pnl:+7.1f} | DD: {max_dd:5.1f} | Trades: {total_trades:>3} | WR: {real_wr:5.1f}% | W:{wins} L:{losses} S:{scratches}")

print(f"RESULT: {split_pnl}")
