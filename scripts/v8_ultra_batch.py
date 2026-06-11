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

print("=== FAST BATCH BACKTEST (OOS 2026) ===")

config_path = "v8_configs/v8_training_config.json"
with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("Loading test data...")
data_path = "data/v8_test_2026.parquet"
full_df = pd.read_parquet(data_path)
full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()

print("Resampling and building Dataset (This takes 1-2 mins, ONCE)...")
df_test = full_df
df_test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
df_test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()

test_dataset = V8DatasetBuilder(config, df_test, df_test_h1, df_test_h4)
test_loader = DataLoader(test_dataset, batch_size=4096, shuffle=False)

# Keep the data tensors in memory since it's small
all_m15, all_h1, all_h4, all_cont, all_y = [], [], [], [], []
for x_m15, x_h1, x_h4, cont_x, y in test_loader:
    all_m15.append(x_m15.to(device))
    all_h1.append(x_h1.to(device))
    all_h4.append(x_h4.to(device))
    all_cont.append(cont_x.to(device))
    all_y.append(y.to(device))

top_models = [
    "brain_OPT-9_S17_PnL+197.pt",
    "brain_OPT-9_S15_PnL+257.pt",
    "brain_OPT-12_S17_PnL+164.pt",
    "brain_OPT-1_S17_PnL+163.pt",
    "brain_OPT-12_S15_PnL+110.pt"
]

results = []

threshold_sim = 0.30
spread = 0.3
tp_mult = 3.0
sl_mult = 1.5
max_hold = 12
cooldown = 4
valid_df = test_dataset.valid_df
n_samples = len(valid_df)

for name in top_models:
    m_path = f"d:/DungLA/client1/v8_configs/hall_of_fame/{name}"
    if not os.path.exists(m_path):
        continue
    
    print(f"\nEvaluating: {name}...")
    state_dict = torch.load(m_path, map_location=device, weights_only=False)
    layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
    num_layers = max(layer_indices) + 1 if layer_indices else 3
    
    config['transformer_params']['num_layers'] = num_layers
    model = V8TransformerModel(config)
    model.load_state_dict(state_dict)
    model.to(device)
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
    
    results.append({
        'name': name, 'pnl': total_pnl, 'pf': pf, 'wr': real_wr, 'dd': max_drawdown, 'trades': total_trades
    })

print("\n" + "="*75)
print(f"{'Model':<35} | {'PnL':>8} | {'PF':>5} | {'WR':>6} | {'DD':>6} | {'Trds':>4}")
print("-" * 75)
results.sort(key=lambda x: x['pnl'], reverse=True)
for r in results:
    print(f"{r['name']:<35} | {r['pnl']:+8.1f} | {r['pf']:5.2f} | {r['wr']:5.1f}% | {r['dd']:6.1f} | {r['trades']:4d}")
