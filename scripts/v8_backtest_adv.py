import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'
import sys
import json
import argparse
import pandas as pd
import numpy as np
import torch
from torch.utils.data import DataLoader

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.v8_engine.transformer_model import V8TransformerModel
from src.v8_engine.dataset_builder import V8DatasetBuilder

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True, help="Path to the model .pt file")
    parser.add_argument("--data", type=str, default="data/v8_test_2026.parquet", help="Path to data parquet")
    return parser.parse_args()

def main():
    args = get_args()
    
    print(f"=== ADVANCED V8 BACKTEST RUNNER ===")
    print(f"Loading Model: {args.model}")
    print(f"Loading Data: {args.data}")
    
    config_path = "v8_configs/v8_training_config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    state_dict = torch.load(args.model, map_location=device)
    layer_indices = [int(k.split('.')[2]) for k in state_dict.keys() if k.startswith('transformer_encoder.layers.')]
    num_layers = max(layer_indices) + 1 if layer_indices else 3
    
    config['transformer_params']['num_layers'] = num_layers
    
    model = V8TransformerModel(config)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    
    if not os.path.exists(args.data):
        print("Data file not found!")
        return
        
    full_df = pd.read_parquet(args.data)
    full_df = full_df[~full_df.index.duplicated(keep='first')].sort_index()
    
    df_test = full_df
    if 'tick_volume' in df_test.columns and 'volume' not in df_test.columns:
        df_test = df_test.rename(columns={'tick_volume': 'volume'})
    df_test_h1 = df_test.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    df_test_h4 = df_test.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
    
    test_dataset = V8DatasetBuilder(config, df_test, df_test_h1, df_test_h4)
    test_loader = DataLoader(test_dataset, batch_size=4096, shuffle=False)
    
    print("Running predictions...")
    all_probs = []
    
    with torch.no_grad():
        for x_m15, x_h1, x_h4, cont_x, y in test_loader:
            x_m15, x_h1, x_h4, cont_x = x_m15.to(device), x_h1.to(device), x_h4.to(device), cont_x.to(device)
            out = model(x_m15, x_h1, x_h4, cont_x)
            probs = torch.softmax(out, dim=1)
            all_probs.append(probs.cpu())
            
    all_probs = torch.cat(all_probs, dim=0)
    
    prob_s2 = all_probs[:, 0]
    prob_b2 = all_probs[:, 4]
    max_trade_probs, trade_dirs = torch.max(torch.stack([prob_s2, prob_b2], dim=1), dim=1)
    
    valid_df = test_dataset.valid_df
    n_samples = len(valid_df)
    
    spread = 0.3
    tp_mult = 3.0
    sl_mult = 1.5
    max_hold = 12
    cooldown = 4
    
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70]
    
    total_active_days = len(set(valid_df.index.date))
    
    print("\n" + "="*90)
    print(f"{'Thr':<6} | {'Trades':<8} | {'Win%':<7} | {'PnL(pip)':<10} | {'MaxDD':<8} | {'PF':<6} | {'T/Day':<8} | {'Cov(%)':<6}")
    print("-" * 90)
    
    for threshold_sim in thresholds:
        signal_mask_sim = max_trade_probs >= threshold_sim
        
        wins = 0
        losses = 0
        scratches = 0
        total_pnl = 0.0
        trade_results = []
        equity = 0.0
        equity_peak = 0.0
        max_drawdown = 0.0
        
        trade_days = []
        next_allowed = 0
        
        for idx in range(n_samples):
            if idx < next_allowed: continue
            if not signal_mask_sim[idx]: continue
            if idx + max_hold >= n_samples: continue
                
            entry_time = valid_df.index[idx]
            if entry_time.hour >= 22 or entry_time.hour < 8:
                continue
                
            row = valid_df.iloc[idx]
            entry_price = row['close']
            atr_val = row.get('atr', 1.5)
            if atr_val <= 0 or np.isnan(atr_val): atr_val = 1.5
            
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
                if fi >= n_samples: break
                check_time = valid_df.index[fi]
                if check_time.hour >= 23 or check_time.hour < 8:
                    result = 'scratch'
                    close_candle = fi
                    break
                    
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
                for h_idx in range(idx + 1, close_candle + 1):
                    if h_idx >= n_samples: break
                    if valid_df.index[h_idx].hour >= 23 or valid_df.index[h_idx].hour < 8:
                        close_candle = h_idx
                        break
                close_candle = min(close_candle, n_samples - 1)
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
            trade_days.append(entry_time.date())
            
        total_trades = wins + losses + scratches
        if total_trades > 0:
            real_wr = wins / total_trades * 100
            gross_win = sum(p for p in trade_results if p > 0)
            gross_loss = abs(sum(p for p in trade_results if p < 0))
            pf = gross_win / gross_loss if gross_loss > 0 else 999.0
            
            unique_days = len(set(trade_days))
            trades_per_day = total_trades / unique_days if unique_days > 0 else 0
            coverage = (unique_days / total_active_days) * 100 if total_active_days > 0 else 0
            
            print(f"{threshold_sim:<6.2f} | {total_trades:<8} | {real_wr:>5.1f}% | {total_pnl:>+8.1f}   | {max_drawdown:>6.1f}   | {pf:<6.2f} | {trades_per_day:<8.1f} | {coverage:>5.1f}%")
        else:
            print(f"{threshold_sim:<6.2f} | 0        | 0.0%    | +0.0       | 0.0      | 0.00   | 0.0      | 0.0%")
    print("="*90)

if __name__ == "__main__":
    main()
